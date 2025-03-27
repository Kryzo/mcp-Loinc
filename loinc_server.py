#!/usr/bin/env python
"""
LOINC API MCP Server
-------------------
This server provides tools to search and retrieve standardized medical terminology from the LOINC database.
It includes endpoints to search for LOINC codes, answer lists, parts, groups, forms, panels, and hierarchical relationships.
"""

import argparse
import os
import sys
import logging
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP
from loinc_api.api import LOINCAPI
from loinc_api.database import LOINCDatabase
from loinc_api.config import DEFAULT_LIMIT, DEFAULT_DATA_VERSION

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    Returns:
        Namespace containing authentication credentials and database file path.
    """
    parser = argparse.ArgumentParser(description="LOINC API MCP Server")
    parser.add_argument("--username", required=True, help="LOINC username")
    parser.add_argument("--password", required=True, help="LOINC password")
    parser.add_argument("--database-file", default="loinc_database.json", help="Path to LOINC database file (CSV or JSON)")
    return parser.parse_args()


def resolve_database_path(database_file: str) -> str:
    """
    Resolve the database file path to an absolute path.
    Args:
        database_file: The database file path (can be relative).
    Returns:
        Absolute path to the database file.
    """
    if not os.path.isabs(database_file):
        database_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), database_file)
    return database_file


def print_file_info(db_path: str) -> None:
    """
    Log information about the database file.
    Args:
        db_path: Absolute path to the database file.
    """
    logger.info(f"Loading LOINC database from: {db_path}")
    exists = os.path.exists(db_path)
    logger.info(f"File exists: {exists}")
    if exists:
        logger.info(f"File size: {os.path.getsize(db_path)} bytes")
        logger.info(f"File permissions: {oct(os.stat(db_path).st_mode)}")
    logger.info(f"Current working directory: {os.getcwd()}")


def initialize_loinc_database(db_path: str) -> LOINCDatabase:
    """
    Initialize the LOINC database.
    Args:
        db_path: Absolute path to the database file.
    Returns:
        An initialized LOINCDatabase instance.
    """
    try:
        loinc_db = LOINCDatabase(db_path)
        success = loinc_db.load_database()
        if success:
            logger.info("LOINC database initialized successfully")
        else:
            logger.warning("LOINC database initialization failed, falling back to API-only mode")
        return loinc_db
    except Exception as e:
        logger.exception("Error initializing LOINC database")
        raise e


def initialize_loinc_api(username: str, password: str) -> LOINCAPI:
    """
    Initialize the LOINC API with HTTP Basic Authentication.
    Args:
        username: LOINC username.
        password: LOINC password.
    Returns:
        An initialized LOINCAPI instance.
    """
    try:
        loinc_api = LOINCAPI(username, password)
        logger.info("LOINC API initialized successfully")
        return loinc_api
    except Exception as e:
        logger.exception("Error initializing LOINC API")
        raise e


# Initialize MCP server
mcp = FastMCP("loinc-api")

# Global variables to hold the API and database
loinc_database: Optional[LOINCDatabase] = None
loinc_api: Optional[LOINCAPI] = None


# ------------------ MCP TOOL ENDPOINTS ------------------ #

@mcp.tool()
def search_loinc_codes(
    query: str,
    limit: int = DEFAULT_LIMIT,
    use_local_db: bool = True,
    component_filter: Optional[str] = None,
    property_filter: Optional[str] = None,
    system_filter: Optional[str] = None,
    class_filter: Optional[str] = None,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Search for LOINC codes matching a query.
    
    This tool searches for LOINC codes that match the provided query. It can search
    in the local database first (if available) and fall back to the API, or go directly
    to the API based on the use_local_db parameter.
    
    Args:
        query: Search term for finding LOINC codes
        limit: Maximum number of results to return
        use_local_db: Whether to search in the local database first
        component_filter: Filter results by component (e.g., "Glucose")
        property_filter: Filter results by property (e.g., "Mass", "Presence")
        system_filter: Filter results by system (e.g., "Blood", "Serum")
        class_filter: Filter results by class (e.g., "PANEL", "SURVEY")
        include_details: Whether to include full details of each LOINC code
        
    Returns:
        Dictionary containing matching LOINC codes and their details
    """
    logger.info(f"Searching for LOINC codes with query: {query}")
    logger.info(f"Parameters: limit={limit}, use_local_db={use_local_db}, include_details={include_details}")
    
    results = []
    api_error = None
    
    # Try local database first if requested and available
    if use_local_db and loinc_database and loinc_database.loaded:
        logger.info("Searching in local database")
        
        # Prepare filter fields
        filter_conditions = {}
        if component_filter:
            filter_conditions["COMPONENT"] = component_filter
        if property_filter:
            filter_conditions["PROPERTY"] = property_filter
        if system_filter:
            filter_conditions["SYSTEM"] = system_filter
        if class_filter:
            filter_conditions["CLASS"] = class_filter
        
        # Search in the local database
        local_results = loinc_database.search(query, limit=limit)
        
        # Apply additional filters
        if filter_conditions:
            filtered_results = []
            for result in local_results:
                matches_all_filters = True
                for field, value in filter_conditions.items():
                    if field in result and value.lower() not in result[field].lower():
                        matches_all_filters = False
                        break
                if matches_all_filters:
                    filtered_results.append(result)
            local_results = filtered_results
        
        if local_results:
            logger.info(f"Found {len(local_results)} results in local database")
            results = local_results
    
    # If no results from local database or local database not used, try the API
    if not results:
        logger.info("Searching using LOINC API")
        
        # Make direct API call with proper parameters
        api_result = loinc_api.search_loincs(query, limit)
        
        # Check for API errors
        if "error" in api_result:
            logger.error(f"API Error: {api_result['error']}")
            api_error = api_result["error"]
        else:
            results = api_result.get("results", [])
            logger.info(f"Found {len(results)} results from API")
            
            # Additional logging to check the response structure
            if not results:
                logger.info(f"API response structure: {api_result.keys()}")
                for key, value in api_result.items():
                    if key != "results":  # We already know results is empty
                        logger.info(f"API response key: {key}, type: {type(value)}, content: {value}")
    
    # Prepare response
    response = {
        "query": query,
        "count": len(results),
        "results": results
    }
    
    # Include API error if there was one
    if api_error:
        response["api_error"] = api_error
        response["status"] = "error"
        response["message"] = "The search was completed with errors. This may be due to API access limitations or incorrect credentials."
    elif not results:
        response["status"] = "success_no_results"
        response["message"] = "The search completed successfully but returned no results. This could be due to no matching LOINC codes, access limitations, or the query may need to be reformulated."
    else:
        response["status"] = "success"
    
    # Include metadata about filters if any were applied
    if any([component_filter, property_filter, system_filter, class_filter]):
        response["filters_applied"] = {
            "component": component_filter,
            "property": property_filter,
            "system": system_filter,
            "class": class_filter
        }
    
    # If not including details, strip down the results
    if not include_details and results:
        simplified_results = []
        for result in results:
            simplified_result = {
                "loinc_code": result.get("LOINC_NUM", ""),
                "long_common_name": result.get("LONG_COMMON_NAME", ""),
                "component": result.get("COMPONENT", ""),
                "property": result.get("PROPERTY", ""),
                "system": result.get("SYSTEM", "")
            }
            simplified_results.append(simplified_result)
        response["results"] = simplified_results
    
    return response


@mcp.tool()
def get_loinc_details(
    loinc_code: str,
    use_local_db: bool = True,
    include_answer_list: bool = True
) -> Dict[str, Any]:
    """
    Get detailed information about a specific LOINC code.
    
    This tool retrieves comprehensive details about a specific LOINC code,
    including its full attributes and optionally its associated answer list.
    
    Args:
        loinc_code: The LOINC code to get details for (e.g., "2339-0" for blood glucose)
        use_local_db: Whether to search in the local database first
        include_answer_list: Whether to include the associated answer list
        
    Returns:
        Dictionary containing details about the LOINC code
    """
    logger.info(f"Getting details for LOINC code: {loinc_code}")
    
    result = None
    
    # Try local database first if requested and available
    if use_local_db and loinc_database and loinc_database.loaded:
        logger.info("Searching in local database")
        result = loinc_database.get_by_loinc_code(loinc_code)
        
        if result:
            logger.info(f"Found LOINC code {loinc_code} in local database")
    
    # If not found in local database or local database not used, try the API
    if not result:
        logger.info("Searching using LOINC API")
        
        # Make API request with the specific LOINC code
        api_params = {"loinc_code": loinc_code}
        api_result = loinc_api.search_loincs(loinc_code, 1)
        
        # Check for API errors
        if "error" in api_result:
            logger.error(f"API Error for '{loinc_code}': {api_result['error']}")
            return {"error": api_result["error"]}
        
        results = api_result.get("results", [])
        if results:
            result = results[0]
            logger.info(f"Found LOINC code {loinc_code} from API")
        else:
            logger.error(f"LOINC code {loinc_code} not found")
            return {"error": f"LOINC code {loinc_code} not found"}
    
    # Prepare the response
    response = {
        "loinc_code": loinc_code,
        "details": result
    }
    
    # Include answer list if requested
    if include_answer_list:
        logger.info(f"Fetching answer list for LOINC code {loinc_code}")
        
        answer_list_result = loinc_api.get_answerlists(loinc_code)
        
        # Check for API errors
        if "error" in answer_list_result:
            logger.warning(f"Error fetching answer list: {answer_list_result['error']}")
            response["answer_list"] = {"error": answer_list_result["error"]}
        else:
            response["answer_list"] = answer_list_result
    
    return response


@mcp.tool()
def get_loinc_panel(
    panel_code: Optional[str] = None,
    panel_name: Optional[str] = None,
    use_local_db: bool = True,
    include_component_details: bool = True
) -> Dict[str, Any]:
    """
    Get information about a LOINC panel and its components.
    
    This tool retrieves information about a LOINC panel (a collection of related
    observations typically ordered together) and its component tests.
    
    Args:
        panel_code: The LOINC code of the panel (e.g., "24331-1" for lipid panel)
        panel_name: Name of the panel to search for (used if panel_code not provided)
        use_local_db: Whether to search in the local database first
        include_component_details: Whether to include details about each component
        
    Returns:
        Dictionary containing panel information and its components
    """
    if not panel_code and not panel_name:
        return {"error": "Either panel_code or panel_name must be provided"}
    
    if panel_code:
        logger.info(f"Getting panel information for LOINC code: {panel_code}")
    else:
        logger.info(f"Searching for panel with name: {panel_name}")
    
    panel_info = None
    
    # If we have a panel code, get its details directly
    if panel_code:
        # First try to get the panel details
        panel_result = get_loinc_details(panel_code, use_local_db, False)
        if "error" in panel_result:
            return panel_result
        
        panel_info = panel_result["details"]
        
        # Verify it's actually a panel
        if panel_info.get("CLASS") != "PANEL":
            return {"error": f"LOINC code {panel_code} is not a panel"}
    
    # If we only have a panel name, search for it
    elif panel_name:
        search_result = search_loinc_codes(
            query=panel_name,
            limit=10,
            use_local_db=use_local_db,
            class_filter="PANEL"
        )
        
        if "error" in search_result:
            return search_result
        
        if not search_result["results"]:
            return {"error": f"No panel found with name: {panel_name}"}
        
        # Use the first matching panel
        panel_info = search_result["results"][0]
        panel_code = panel_info.get("LOINC_NUM")
    
    # Now get the panel components via API
    logger.info(f"Fetching components for panel: {panel_code}")
    panel_components_result = loinc_api.search_panels(panel_code)
    
    # Check for API errors
    if "error" in panel_components_result:
        logger.error(f"Error fetching panel components: {panel_components_result['error']}")
        return {"error": panel_components_result["error"]}
    
    components = panel_components_result.get("components", [])
    
    # If requested and we have component codes, get the details for each component
    if include_component_details and components:
        logger.info(f"Fetching details for {len(components)} panel components")
        
        for i, component in enumerate(components):
            component_code = component.get("loinc_code")
            if component_code:
                component_details = get_loinc_details(component_code, use_local_db, False)
                if "error" not in component_details:
                    components[i]["details"] = component_details["details"]
    
    # Prepare the response
    response = {
        "panel_code": panel_code,
        "panel_info": panel_info,
        "component_count": len(components),
        "components": components
    }
    
    return response


@mcp.tool()
def search_loinc_forms(
    query: str,
    limit: int = DEFAULT_LIMIT,
    include_questions: bool = True
) -> Dict[str, Any]:
    """
    Search for LOINC standardized forms and questionnaires.
    
    This tool searches for standardized assessment forms and questionnaires defined in LOINC,
    optionally including their component questions.
    
    Args:
        query: Search term for finding forms
        limit: Maximum number of results to return
        include_questions: Whether to include the questions in each form
        
    Returns:
        Dictionary containing matching forms and their details
    """
    logger.info(f"Searching for LOINC forms with query: {query}")
    
    # Search for forms using the API
    forms_result = loinc_api.search_forms(query, limit)
    
    # Check for API errors
    if "error" in forms_result:
        logger.error(f"API Error: {forms_result['error']}")
        return {"error": forms_result["error"]}
    
    forms = forms_result.get("forms", [])
    logger.info(f"Found {len(forms)} forms matching query: {query}")
    
    # If requested and we have forms, get the questions for each form
    if include_questions and forms:
        logger.info(f"Fetching questions for {len(forms)} forms")
        
        for i, form in enumerate(forms):
            form_code = form.get("loinc_code")
            if form_code:
                # Use the panel endpoint to get the form questions (form is essentially a panel)
                form_details = get_loinc_panel(panel_code=form_code, include_component_details=True)
                if "error" not in form_details:
                    forms[i]["questions"] = form_details.get("components", [])
    
    # Prepare the response
    response = {
        "query": query,
        "count": len(forms),
        "forms": forms
    }
    
    return response


@mcp.tool()
def get_loinc_top2000() -> Dict[str, Any]:
    """
    Get the top 2000 most commonly used LOINC codes.
    
    This tool retrieves information about the most frequently used LOINC codes,
    which are valuable for healthcare IT implementations.
    
    Returns:
        Dictionary containing the top 2000 LOINC codes and their details
    """
    logger.info("Fetching Top 2000 LOINC codes")
    
    # Use the API to get the top 2000 codes
    top2000_result = loinc_api.get_top2000()
    
    # Check for API errors
    if "error" in top2000_result:
        logger.error(f"API Error: {top2000_result['error']}")
        return {"error": top2000_result["error"]}
    
    codes = top2000_result.get("codes", [])
    logger.info(f"Retrieved {len(codes)} top LOINC codes")
    
    # Prepare the response
    response = {
        "count": len(codes),
        "codes": codes
    }
    
    return response


@mcp.tool()
def get_loinc_hierarchy(
    parent_code: Optional[str] = None,
    child_code: Optional[str] = None,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    Get the hierarchical relationships between LOINC terms.
    
    This tool retrieves the hierarchical relationships (parent-child) between LOINC terms.
    You can either get the children of a parent code or the parents of a child code.
    
    Args:
        parent_code: LOINC code to find children of
        child_code: LOINC code to find parents of
        max_depth: Maximum depth of hierarchy to return
        
    Returns:
        Dictionary containing hierarchical relationships
    """
    if not parent_code and not child_code:
        return {"error": "Either parent_code or child_code must be provided"}
    
    logger.info(f"Getting hierarchy for LOINC code: {parent_code or child_code}")
    
    # Make API request
    hierarchy_result = loinc_api.get_multiaxial(parent=parent_code, child=child_code)
    
    # Check for API errors
    if "error" in hierarchy_result:
        logger.error(f"API Error: {hierarchy_result['error']}")
        return {"error": hierarchy_result["error"]}
    
    # Prepare the response
    response = {
        "direction": "children" if parent_code else "parents",
        "root_code": parent_code or child_code,
        "max_depth": max_depth,
        "hierarchy": hierarchy_result
    }
    
    return response


def test_loinc_api_connection(username: str, password: str) -> None:
    """
    Test the LOINC API connection with multiple search terms.
    
    Args:
        username: LOINC username
        password: LOINC password
    """
    logger.info("=== Testing LOINC API Connection ===")
    
    try:
        # Initialize the API
        test_api = initialize_loinc_api(username, password)
        
        # Try different search terms
        test_terms = ["glucose", "2339-0", "hemoglobin", "lipid panel"]
        
        for term in test_terms:
            logger.info(f"Testing API with search term: '{term}'...")
            result = test_api.search_loincs(term)
            
            if "error" in result:
                logger.error(f"API Error for '{term}': {result['error']}")
                continue
                
            # Print success and result count
            results_list = result.get("results", [])
            result_count = len(results_list)
            logger.info(f"API test for '{term}' successful! Found {result_count} results")
            
            # Print the first result for verification
            if result_count > 0:
                first_result = results_list[0]
                logger.info(f"First result for '{term}': {first_result}")
                
            # Log the response summary if available
            if "responsesummary" in result:
                logger.info(f"Response summary for '{term}': {result['responsesummary']}")
            
    except Exception as e:
        logger.exception(f"Error testing LOINC API: {e}")


# ------------------ MAIN EXECUTION ------------------ #

def main():
    """
    Main entry point for the LOINC API MCP Server.
    Initializes the API and LOINC database, logs file details, and starts the MCP server.
    """
    global loinc_api, loinc_database
    
    # Parse command-line arguments
    args = parse_arguments()
    
    # Test the LOINC API connection
    test_loinc_api_connection(args.username, args.password)
    
    # Resolve database file path
    db_path = resolve_database_path(args.database_file)
    
    # Log information about the database file
    print_file_info(db_path)
    
    try:
        # Initialize the LOINC database (if file exists)
        if os.path.exists(db_path):
            loinc_database = initialize_loinc_database(db_path)
        else:
            logger.warning(f"Database file not found: {db_path}")
            logger.info("Running in API-only mode")
            loinc_database = None
        
        # Initialize the LOINC API with username and password
        loinc_api = initialize_loinc_api(args.username, args.password)
        
        # Start the MCP server
        logger.info("Starting LOINC API MCP Server")
        mcp.run()
        
    except Exception as e:
        logger.exception("Error starting LOINC API MCP Server")
        sys.exit(1)


if __name__ == "__main__":
    main()
