"""
LOINC API Client
---------------
Client for interacting with the LOINC API to retrieve standardized medical terminology.
"""

import requests
from requests.auth import HTTPBasicAuth
import logging
import json
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class LOINCAPI:
    """
    Client for the LOINC API, which provides access to standardized medical terminology.
    """
    
    def __init__(self, username: str, password: str, base_url: str = "https://loinc.regenstrief.org/searchapi/"):
        """
        Initialize the LOINC API client.
        
        Args:
            username: LOINC username for authentication
            password: LOINC password for authentication
            base_url: Base URL for the LOINC API
        """
        self.username = username
        self.password = password
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {"Accept": "application/json"}
        logger.info(f"Initialized LOINC API client with base URL: {base_url}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the LOINC API using HTTP Basic Authentication.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            
        Returns:
            JSON response from the API
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            # Ensure params are properly formatted as strings
            formatted_params = {}
            if params:
                for key, value in params.items():
                    formatted_params[key] = str(value)
            
            logger.debug(f"Making request to {url} with params: {formatted_params}")
            prepared_url = requests.Request('GET', url, params=formatted_params).prepare().url
            logger.info(f"Full URL with params would be: {prepared_url}")
            
            response = requests.get(url, auth=self.auth, headers=self.headers, params=formatted_params)
            # Log detailed information about the request
            logger.info(f"Request URL: {response.request.url}")
            logger.info(f"Request headers: {response.request.headers}")
            
            # Check if there was an error and log more details
            if response.status_code != 200:
                logger.error(f"Error response status code: {response.status_code}")
                logger.error(f"Error response content: {response.text}")
                return {"error": f"HTTP error {response.status_code}: {response.reason}. Response: {response.text}"}
            
            # Log the raw response content for debugging
            logger.info(f"Response status code: {response.status_code}")
            logger.debug(f"Response content: {response.text[:1000]}...")  # Truncate long responses
            
            # Parse the response as JSON
            try:
                result = response.json()
                
                # Standardize LOINC API response to use lowercase 'results' key
                # LOINC API uses 'Results' (capital R) in its response
                standardized_result = {}
                
                # Copy over any metadata or non-result keys
                for key, value in result.items():
                    if key != 'Results':
                        standardized_result[key.lower()] = value
                
                # Handle the actual results - could be in 'Results' or somewhere else
                if 'Results' in result:
                    standardized_result['results'] = result['Results']
                    logger.info(f"Found {len(result['Results'])} items in 'Results' key")
                    return standardized_result
                elif 'results' in result:
                    standardized_result['results'] = result['results']
                    return standardized_result
                else:
                    logger.warning(f"Response doesn't contain 'Results' or 'results' key. Keys found: {result.keys()}")
                    # Create a reasonable default
                    standardized_result['results'] = []
                    standardized_result['raw_response'] = result
                    
                    # If the response is a list, use it as results
                    if isinstance(result, list):
                        logger.info("Response is a list, using it as results")
                        standardized_result['results'] = result
                    
                    return standardized_result
                
            except json.JSONDecodeError:
                logger.error("Response is not valid JSON")
                logger.error(f"Raw response content: {response.text[:500]}...")
                return {
                    "error": "Invalid JSON response from API",
                    "raw_response": response.text[:1000],
                    "results": []
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {e}")
            return {"error": str(e), "results": []}

    
    def search_loincs(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for LOINC codes matching a query.
        
        Args:
            query: Search term
            limit: Maximum number of results to return
        
        Returns:
            Dictionary containing matching LOINC codes and their details
        """
        logger.info(f"Searching for LOINC codes with query: '{query}', limit: {limit}")
        
        # Try with Query parameter (official docs)
        params = {
            "Query": query,
            "Limit": limit
        }
        
        result = self._make_request("loincs", params)
        
        # If empty results and no error, try with lowercase parameters as fallback
        if "error" not in result and not result.get("results", []):
            logger.info("No results found with capitalized parameters, trying lowercase")
            lowercase_params = {
                "query": query,
                "limit": limit
            }
            lowercase_result = self._make_request("loincs", lowercase_params)
            
            # Use the lowercase result if it has results or if both have no results
            if "results" in lowercase_result and (len(lowercase_result["results"]) > 0 or "error" in result):
                logger.info(f"Lowercase parameters returned {len(lowercase_result.get('results', []))} results")
                return lowercase_result
        
        logger.info(f"Returning {len(result.get('results', []))} results")
        return result
    
    def get_answerlists(self, loinc_code: str) -> Dict[str, Any]:
        """
        Get standardized answer options for a specific LOINC code.
        
        Args:
            loinc_code: LOINC code to get answer lists for
            
        Returns:
            Dictionary containing answer options for the LOINC code
        """
        params = {
            "LoincNumber": loinc_code
        }
        return self._make_request("answerlists", params)
    
    def search_parts(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for LOINC parts matching a query.
        
        Args:
            query: Search term
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing matching LOINC parts
        """
        params = {
            "Query": query,
            "Limit": limit
        }
        return self._make_request("parts", params)
    
    def search_groups(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for LOINC groups matching a query.
        
        Args:
            query: Search term
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing matching LOINC groups
        """
        params = {
            "Query": query,
            "Limit": limit
        }
        return self._make_request("groups", params)
    
    def get_multiaxial(self, parent: str = None, child: str = None) -> Dict[str, Any]:
        """
        Get hierarchical relationships between LOINC terms.
        
        Args:
            parent: Parent LOINC code to find children of
            child: Child LOINC code to find parents of
            
        Returns:
            Dictionary containing hierarchical relationships
        """
        params = {}
        if parent:
            params["Parent"] = parent
        if child:
            params["Child"] = child
            
        return self._make_request("multiaxial", params)
    
    def search_forms(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for standardized assessment forms and questionnaires.
        
        Args:
            query: Search term
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing matching forms
        """
        params = {
            "Query": query,
            "Limit": limit
        }
        return self._make_request("forms", params)
    
    def search_panels(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for LOINC panels (collections of related observations).
        
        Args:
            query: Search term
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing matching panels
        """
        params = {
            "Query": query,
            "Limit": limit
        }
        return self._make_request("panels", params)
    
    def get_top2000(self) -> Dict[str, Any]:
        """
        Get the most commonly used LOINC codes.
        
        Returns:
            Dictionary containing the top 2000 LOINC codes
        """
        return self._make_request("top2000")
