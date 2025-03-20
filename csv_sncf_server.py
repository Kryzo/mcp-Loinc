#!/usr/bin/env python3
"""
Enhanced SNCF API MCP Server
This version properly handles JSON serialization and prevents log output from interfering with the JSON stream
"""

from mcp.server.fastmcp import FastMCP
import argparse
import os.path
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Callable

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging to file only (no stdout/stderr)
log_file = os.path.join('logs', f"sncf_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sncf_mcp')

# Prevent other loggers from writing to stdout/stderr
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).propagate = False
    logging.getLogger(name).handlers = []

# Import the SNCF API classes - catch import errors
try:
    from sncf_api.api import SNCFAPI
    from sncf_api.csv_station_finder import CSVStationFinder
except ImportError as e:
    logger.error(f"Import error: {e}")
    print(f"Error importing SNCF API modules: {e}", file=sys.stderr)
    sys.exit(1)

# Custom JSON encoder to handle non-serializable objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if hasattr(obj, 'to_json'):
                return obj.to_json()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)
        except:
            return "[Non-serializable Object]"

# Function decorator that ensures responses are JSON serializable
def ensure_json_serializable(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # Verify JSON serialization before returning
            try:
                json.dumps(result, cls=CustomJSONEncoder)
                return result
            except TypeError as e:
                logger.error(f"JSON serialization error in {func.__name__}: {e}")
                return {"error": "Response serialization error", "details": str(e)}
                
        except Exception as e:
            error_message = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Error in {func.__name__}: {error_message}\n{stack_trace}")
            return {"error": error_message}
    
    # Preserve function metadata for FastMCP
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    
    return wrapper

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="SNCF API MCP Server with CSV Station Database")
    parser.add_argument("--api-key", required=True, help="SNCF API key")
    parser.add_argument("--csv-file", default="train_stations_europe.csv", help="Path to train stations CSV file")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    args = parser.parse_args()
    
    # Set log level
    logger.setLevel(getattr(logging, args.log_level.upper()))
    
    # Create an MCP server
    mcp = FastMCP("sncf-csv-api")
    
    # Initialize the SNCF API
    try:
        sncf_api = SNCFAPI(args.api_key)
        logger.info("SNCF API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize SNCF API: {e}")
        print(f"Error initializing SNCF API: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize the CSV Station Finder
    csv_file_path = args.csv_file
    if not os.path.isabs(csv_file_path):
        # If relative path, make it relative to current directory
        csv_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), csv_file_path)
    
    try:
        station_finder = CSVStationFinder(csv_file_path)
        logger.info(f"CSV Station Finder initialized with {csv_file_path}")
    except Exception as e:
        logger.error(f"Failed to initialize CSV Station Finder: {e}")
        print(f"Error initializing CSV Station Finder: {e}", file=sys.stderr)
        sys.exit(1)

    # Tool definitions with the ensure_json_serializable decorator
    @mcp.tool()
    @ensure_json_serializable
    def search_places(query: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Search for places (stations, addresses, POIs) using the CSV database
        
        Args:
            query: The search query (e.g., "Paris", "Gare de Lyon")
            count: Maximum number of results to return (default: 10)
            
        Returns:
            A list of places matching the query
        """
        return station_finder.search_stations(query, limit=count)

    @mcp.tool()
    @ensure_json_serializable
    def get_journey(
        from_place: str, 
        to_place: str, 
        datetime: Optional[str] = None,
        datetime_represents: str = "departure"
    ) -> Dict[str, Any]:
        """
        Plan a journey between two places using the SNCF API
        
        Args:
            from_place: The starting point (can be a place ID or coordinates)
            to_place: The destination (can be a place ID or coordinates)
            datetime: Date and time in format YYYYMMDDTHHMMSS (default: now)
            datetime_represents: Either "departure" or "arrival" (default: departure)
            
        Returns:
            Journey information including sections, duration, etc.
        """
        return sncf_api.plan_journey(
            from_place=from_place,
            to_place=to_place,
            datetime=datetime,
            datetime_represents=datetime_represents
        )

    @mcp.tool()
    @ensure_json_serializable
    def get_departures(
        station_id: str,
        count: int = 5,
        datetime: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get next departures from a station
        
        Args:
            station_id: The ID of the station (stop_area)
            count: Maximum number of departures to return (default: 5)
            datetime: Date and time in format YYYYMMDDTHHMMSS (default: now)
            
        Returns:
            A list of upcoming departures
        """
        return sncf_api.get_departures(
            station_id=station_id,
            count=count,
            datetime=datetime
        )

    @mcp.tool()
    @ensure_json_serializable
    def check_disruptions(
        coverage: str = "sncf",
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Check for current disruptions in the transport network
        
        Args:
            coverage: The coverage area (default: sncf for the French national railway)
            count: Maximum number of disruptions to return (default: 10)
            
        Returns:
            A list of current disruptions
        """
        return sncf_api.check_disruptions(coverage, count)

    @mcp.tool()
    @ensure_json_serializable
    def get_regions() -> List[Dict[str, Any]]:
        """
        Get all available regions (coverage) from the SNCF API
        
        Returns:
            A list of available regions with their IDs and details
        """
        return sncf_api.get_regions()

    @mcp.tool()
    @ensure_json_serializable
    def get_lines(
        coverage: str = "sncf",
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get transport lines from the SNCF API
        
        Args:
            coverage: The coverage area (default: sncf)
            count: Maximum number of lines to return (default: 10)
            
        Returns:
            A list of transport lines
        """
        return sncf_api.networks.get_lines(coverage, count)

    @mcp.tool()
    @ensure_json_serializable
    def get_places_nearby(
        lon: float,
        lat: float,
        distance: int = 500,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get places nearby a specific location
        
        Args:
            lon: Longitude of the location
            lat: Latitude of the location
            distance: Search radius in meters (default: 500)
            count: Maximum number of places to return (default: 10)
            
        Returns:
            A list of places near the specified location
        """
        return sncf_api.search.places_nearby(lon, lat, distance=distance, count=count)

    @mcp.tool()
    @ensure_json_serializable
    def find_station_by_name(
        city: str,
        station_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find a station by city and station name using the CSV database
        
        Args:
            city: The city name (e.g., "Paris", "Marseille")
            station_name: The station name (e.g., "Gare de Lyon", "Saint-Charles"), optional
            
        Returns:
            Station information including ID
        """
        result = station_finder.find_station_by_name(city, station_name)
        if result:
            return result
        else:
            return {"error": f"Could not find station in {city}"}

    @mcp.tool()
    @ensure_json_serializable
    def find_station_by_coordinates(
        lat: float,
        lon: float,
        max_distance_km: float = 2.0
    ) -> Dict[str, Any]:
        """
        Find a station by coordinates using the CSV database
        
        Args:
            lat: Latitude
            lon: Longitude
            max_distance_km: Maximum distance in kilometers (default: 2.0)
            
        Returns:
            Station information including ID
        """
        result = station_finder.find_station_by_coordinates(lat, lon, max_distance_km)
        if result:
            return result
        else:
            return {"error": f"Could not find station near coordinates ({lat}, {lon})"}

    @mcp.tool()
    @ensure_json_serializable
    def list_all_cities() -> List[str]:
        """
        List all cities with train stations from the CSV database
        
        Returns:
            List of city names
        """
        return station_finder.get_all_cities()

    @mcp.tool()
    @ensure_json_serializable
    def journey_with_city_names(
        from_city: str,
        to_city: str,
        from_station: Optional[str] = None,
        to_station: Optional[str] = None,
        datetime: Optional[str] = None,
        datetime_represents: str = "departure"
    ) -> Dict[str, Any]:
        """
        Plan a journey between two cities using city and station names
        
        Args:
            from_city: The departure city (e.g., "Paris")
            to_city: The arrival city (e.g., "Marseille")
            from_station: The departure station (e.g., "Gare de Lyon"), optional
            to_station: The arrival station (e.g., "Saint-Charles"), optional
            datetime: Date and time in format YYYYMMDDTHHMMSS (default: now)
            datetime_represents: Either "departure" or "arrival" (default: departure)
            
        Returns:
            Journey information including sections, duration, etc.
        """
        # Find stations based on city and station names
        departure_station, arrival_station = station_finder.find_journey_with_city_names(
            from_city=from_city,
            to_city=to_city,
            from_station=from_station,
            to_station=to_station
        )
        
        if not departure_station:
            return {"error": f"Could not find station in {from_city}"}
            
        if not arrival_station:
            return {"error": f"Could not find station in {to_city}"}
            
        # Plan journey using station IDs
        return sncf_api.plan_journey(
            from_place=departure_station['id'],
            to_place=arrival_station['id'],
            datetime=datetime,
            datetime_represents=datetime_represents
        )

    @mcp.tool()
    @ensure_json_serializable
    def list_stations_in_city(
        city: str
    ) -> Dict[str, Any]:
        """
        List all stations in a specific city
        
        Args:
            city: City name
            
        Returns:
            List of stations in the city
        """
        stations = station_finder.find_stations_by_city(city)
        if stations:
            return {
                "city": city,
                "count": len(stations),
                "stations": stations
            }
        else:
            return {"error": f"No stations found for city: {city}"}

    # Start the server
    print(f"Starting SNCF CSV Station Finder MCP Server...")
    print(f"Using CSV file: {csv_file_path}")
    print(f"Logs written to: {log_file}")
    mcp.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error in MCP server: {e}", exc_info=True)
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
