#!/usr/bin/env python
"""
SNCF API MCP Server
-------------------
This server provides tools to search and plan journeys based on a CSV station database and the SNCF API.
It includes endpoints to look up the coordinates (latitude and longitude) of all stations in a city,
and to plan a journey using those coordinates.
"""

import argparse
import os
import sys
import logging
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP
from sncf_api.api import SNCFAPI
from sncf_api.csv_station_finder import CSVStationFinder
from sncf_api.config import DEFAULT_DATA_FRESHNESS, DEFAULT_DEPTH, DEFAULT_COUNT
from sncf_api.stations import StationsAPI

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    Returns:
        Namespace containing API key and CSV file path.
    """
    parser = argparse.ArgumentParser(description="SNCF API MCP Server")
    parser.add_argument("--api-key", required=True, help="SNCF API key")
    parser.add_argument("--csv-file", default="train_stations_europe.csv", help="Path to train stations CSV file")
    return parser.parse_args()


def resolve_csv_path(csv_file: str) -> str:
    """
    Resolve the CSV file path to an absolute path.
    Args:
        csv_file: The CSV file path (can be relative).
    Returns:
        Absolute path to the CSV file.
    """
    if not os.path.isabs(csv_file):
        csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), csv_file)
    return csv_file


def print_file_info(csv_path: str) -> None:
    """
    Log information about the CSV file.
    Args:
        csv_path: Absolute path to the CSV file.
    """
    logger.info(f"Loading train station data from: {csv_path}")
    exists = os.path.exists(csv_path)
    logger.info(f"File exists: {exists}")
    if exists:
        logger.info(f"File size: {os.path.getsize(csv_path)} bytes")
        logger.info(f"File permissions: {oct(os.stat(csv_path).st_mode)}")
    logger.info(f"Current working directory: {os.getcwd()}")


def initialize_csv_station_finder(csv_path: str) -> CSVStationFinder:
    """
    Initialize the CSVStationFinder.
    Args:
        csv_path: Absolute path to the CSV file.
    Returns:
        An initialized CSVStationFinder instance.
    """
    try:
        csv_station_finder = CSVStationFinder(csv_path)
        logger.info("CSV station finder initialized successfully")
        return csv_station_finder
    except Exception as e:
        logger.exception("Error initializing CSV station finder")
        raise e


def initialize_sncf_api(api_key: str) -> SNCFAPI:
    """
    Initialize the SNCF API.
    Args:
        api_key: SNCF API key.
    Returns:
        An initialized SNCFAPI instance.
    """
    try:
        sncf_api = SNCFAPI(api_key)
        logger.info("SNCF API initialized successfully")
        return sncf_api
    except Exception as e:
        logger.exception("Error initializing SNCF API")
        raise e


# Initialize MCP server
mcp = FastMCP("sncf-api")

# Global variables to hold the API and CSV finder
csv_station_finder: Optional[CSVStationFinder] = None
sncf_api: Optional[SNCFAPI] = None


# ------------------ MCP TOOL ENDPOINTS ------------------ #

@mcp.tool()
def plan_journey_by_city_names(
    from_city: str,
    to_city: str,
    datetime: Optional[str] = None,
    datetime_represents: str = "departure",
    include_station_details: bool = False
) -> Dict[str, Any]:
    """
    All-in-one journey planning tool that takes city names and returns journey details.
    This function handles the entire process:
    1. Finds stations in both cities
    2. Extracts their coordinates and IDs
    3. Uses the station IDs to plan a journey
    
    Args:
        from_city: Departure city name (e.g., "Paris").
        to_city: Destination city name (e.g., "Marseille").
        datetime: Date and time in format YYYYMMDDTHHMMSS (default: now).
        datetime_represents: "departure" or "arrival" (default: "departure").
        include_station_details: Whether to include station details in the response.
    
    Returns:
        A dictionary containing journey details and optionally station information.
    """
    # Step 1: Find stations for both cities
    csv_station_finder._add_hardcoded_stations()
    from_stations = csv_station_finder.find_stations_by_city(from_city)
    to_stations = csv_station_finder.find_stations_by_city(to_city)
    
    if not from_stations:
        return {"error": f"No stations found for departure city: {from_city}"}
    if not to_stations:
        return {"error": f"No stations found for destination city: {to_city}"}
    
    logger.info(f"Found {len(from_stations)} stations for departure city: {from_city}")
    logger.info(f"Found {len(to_stations)} stations for destination city: {to_city}")
    
    # Step 2: Filter stations with valid IDs and prioritize main train stations over city-level locations
    # First, filter out stations without IDs
    from_stations_with_id = [s for s in from_stations if s.get("id")]
    to_stations_with_id = [s for s in to_stations if s.get("id")]
    
    if not from_stations_with_id:
        return {"error": f"No valid station IDs found for {from_city}"}
    if not to_stations_with_id:
        return {"error": f"No valid station IDs found for {to_city}"}
    
    # Step 3: Select the most appropriate stations
    # Define a scoring function to prioritize main train stations and avoid city-level locations
    def station_score(station):
        score = 0
        # Strongly prefer main stations
        if station.get("is_main_station", False):
            score += 100
        # Avoid city-level locations
        if station.get("is_city", False):
            score -= 50
        # Prefer stations with "Gare" in the name
        if "Gare" in station.get("name", ""):
            score += 30
        return score
    
    # Sort stations by score (highest first)
    from_stations_with_id.sort(key=station_score, reverse=True)
    to_stations_with_id.sort(key=station_score, reverse=True)
    
    # Log the sorted stations for debugging
    logger.info(f"Sorted departure stations: {[s['name'] for s in from_stations_with_id]}")
    logger.info(f"Sorted arrival stations: {[s['name'] for s in to_stations_with_id]}")
    
    from_station = from_stations_with_id[0]
    to_station = to_stations_with_id[0]
    
    from_station_id = from_station["id"]
    to_station_id = to_station["id"]
    
    # Extract coordinates for informational purposes
    from_coords = from_station.get("coord", {})
    to_coords = to_station.get("coord", {})
    
    from_lat = from_coords.get("lat")
    from_lon = from_coords.get("lon")
    to_lat = to_coords.get("lat")
    to_lon = to_coords.get("lon")
    
    logger.info(f"Planning journey from {from_station['name']} ({from_lat}, {from_lon}) to {to_station['name']} ({to_lat}, {to_lon})")
    logger.info(f"Using station IDs: {from_station_id} to {to_station_id}")
    
    # Step 4: Plan the journey using station IDs
    journey_result = sncf_api.plan_journey(
        from_place=from_station_id,
        to_place=to_station_id,
        datetime=datetime,
        datetime_represents=datetime_represents
    )
    
    # Step 5: Prepare the response
    result = {
        "journey": journey_result
    }
    
    # Include station details if requested
    if include_station_details:
        result["stations"] = {
            "from": {
                "name": from_station["name"],
                "id": from_station_id,
                "coordinates": {"latitude": from_lat, "longitude": from_lon},
                "is_main_station": from_station.get("is_main_station", False),
                "is_city": from_station.get("is_city", False)
            },
            "to": {
                "name": to_station["name"],
                "id": to_station_id,
                "coordinates": {"latitude": to_lat, "longitude": to_lon},
                "is_main_station": to_station.get("is_main_station", False),
                "is_city": to_station.get("is_city", False)
            }
        }
    
    return result

@mcp.tool()
def check_disruptions(
    coverage: str = "sncf",
    count: int = 10,
    station_id: Optional[str] = None,
    line_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,

    fetch_train_details: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Check for current disruptions in the SNCF transport network.
    
    Args:
        coverage: The coverage area to use for the request.
        count: The maximum number of disruptions to return.
        station_id: Filter disruptions affecting a specific station.
        line_id: Filter disruptions affecting a specific line.
        since: Only disruptions valid after this date (format YYYYMMDDTHHMMSS).
        until: Only disruptions valid before this date (format YYYYMMDDTHHMMSS).
        fetch_train_details: Whether to fetch additional details about affected trains.
        debug: Whether to include debug information in the response.
        
    Returns:
        A dictionary containing information about the disruptions.
    """
    if sncf_api is None:
        return {"error": "SNCF API not initialized"}
    
    try:
        # Get disruptions from the API
        disruptions = sncf_api.check_disruptions(
            coverage=coverage,
            count=count,
            station_id=station_id,
            line_id=line_id,
            since=since,
            until=until
        )
        
        return {
            "total_count": len(disruptions),
            "disruptions": disruptions
        }
    except Exception as e:
        logger.exception(f"Error checking disruptions: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def get_station_schedule(
    city_name: Optional[str] = None,
    station_name: Optional[str] = None,
    station_id: Optional[str] = None,
    count: int = 10,
    datetime: Optional[str] = None,
    duration: Optional[int] = None,
    data_freshness: str = DEFAULT_DATA_FRESHNESS
) -> Dict[str, Any]:
    """
    Get both departures and arrivals schedule for a station.
    
    This tool finds stations in the specified city and returns schedule information.
    If multiple stations exist in the city and no specific station is provided,
    it will return information about all available stations.
    If a station_id is provided, it will directly use that instead of searching by city/name.
    
    You can search for stations by providing either:
    1. A city name (e.g., "Paris")
    2. A station name (e.g., "Montparnasse")
    3. Both city and station name (e.g., city="Paris", station="Montparnasse")
    4. A direct station ID if you know it
    
    Args:
        city_name: Name of the city to search for stations
        station_name: Optional name of a specific station to filter by
        station_id: Optional direct station ID (if you know the exact ID)
        count: Number of departures/arrivals to return
        datetime: Optional datetime to start from (ISO format)
        duration: Optional duration in seconds
        data_freshness: Data freshness level (realtime or base_schedule)
        
    Returns:
        Dictionary with station information and schedules
    """
    global csv_station_finder, sncf_api
    if not csv_station_finder:
        return {"error": "CSV station finder not initialized"}
    
    if not sncf_api:
        return {"error": "SNCF API not initialized"}
    
    try:
        stations = []
        
        # If station_id is provided, use it directly
        if station_id:
            # Format the ID if needed
            if not station_id.startswith("stop_area:"):
                station_id = f"stop_area:SNCF:{station_id}"
                
            # Create a minimal station object
            stations = [{
                "id": station_id,
                "name": station_id,  # We don't know the name, but it's not critical
                "coordinates": {"lat": 0, "lon": 0}  # Placeholder coordinates
            }]
        else:
            # If we have a station name but no city, try to find it directly via API search
            if station_name and not city_name:
                logger.info(f"Searching for station by name: {station_name}")
                
                # Use the SNCF API search functionality to find the station
                search_results = sncf_api.search.places(query=station_name, count=5)
                
                # Filter for stop_area type (stations)
                station_results = [
                    place for place in search_results 
                    if place.get("type") == "stop_area"
                ]
                
                if station_results:
                    # Create station objects from search results
                    stations = []
                    for result in station_results:
                        stations.append({
                            "id": result.get("id", ""),
                            "name": result.get("name", ""),
                            "coordinates": result.get("coordinates", {"lat": 0, "lon": 0})
                        })
                    
                    logger.info(f"Found {len(stations)} stations matching '{station_name}'")
                else:
                    return {"error": f"No stations found matching '{station_name}'"}
            
            # If we have a city name, search for stations in that city
            elif city_name:
                # Ensure hardcoded stations are added
                csv_station_finder._add_hardcoded_stations()
                
                # Find all stations in the city
                stations = csv_station_finder.find_stations_by_city(city_name)
                
                if not stations:
                    # If no stations found in CSV, try using the API search
                    search_query = city_name
                    if station_name:
                        search_query = f"{city_name} {station_name}"
                    
                    logger.info(f"No stations found in CSV for {city_name}, trying API search with: {search_query}")
                    search_results = sncf_api.search.places(query=search_query, count=5)
                    
                    # Filter for stop_area type (stations)
                    station_results = [
                        place for place in search_results 
                        if place.get("type") == "stop_area"
                    ]
                    
                    if station_results:
                        # Create station objects from search results
                        stations = []
                        for result in station_results:
                            stations.append({
                                "id": result.get("id", ""),
                                "name": result.get("name", ""),
                                "coordinates": result.get("coordinates", {"lat": 0, "lon": 0})
                            })
                        
                        logger.info(f"Found {len(stations)} stations via API search for '{search_query}'")
                    else:
                        return {"error": f"No stations found for '{search_query}'"}
                else:
                    logger.info(f"Found {len(stations)} stations for city: {city_name}")
                
                # If station_name is provided, filter stations
                if station_name and len(stations) > 1:
                    # If we have multiple stations and a station name, try to find the best match
                    # First, try using the StationFinder if available
                    try:
                        from sncf_api.station_finder import StationFinder
                        station_finder = StationFinder(sncf_api)
                        best_match = station_finder.find_station_by_name(city_name, station_name)
                        
                        if best_match:
                            logger.info(f"Found best match using StationFinder: {best_match.get('name')}")
                            stations = [{
                                "id": best_match.get("id", ""),
                                "name": best_match.get("name", ""),
                                "coordinates": best_match.get("coordinates", best_match.get("coord", {"lat": 0, "lon": 0}))
                            }]
                    except (ImportError, AttributeError) as e:
                        logger.warning(f"Could not use StationFinder: {str(e)}")
                        
                        # Fall back to simple text matching if StationFinder fails
                        normalized_station_name = csv_station_finder._normalize_text(station_name)
                        matching_stations = []
                        
                        # Try exact substring match
                        for station in stations:
                            station_name_normalized = csv_station_finder._normalize_text(station['name'])
                            if normalized_station_name in station_name_normalized:
                                matching_stations.append(station)
                        
                        # Try partial matching if no exact matches
                        if not matching_stations:
                            for station in stations:
                                if station_name.lower() in station['name'].lower() or station['name'].lower() in station_name.lower():
                                    matching_stations.append(station)
                        
                        stations = matching_stations
                        
                        if not stations:
                            # If no matches found, try a direct API search as a last resort
                            search_query = f"{city_name} {station_name}"
                            logger.info(f"No matching stations found, trying direct API search with: {search_query}")
                            
                            search_results = sncf_api.search.places(query=search_query, count=5)
                            station_results = [
                                place for place in search_results 
                                if place.get("type") == "stop_area"
                            ]
                            
                            if station_results:
                                # Create station objects from search results
                                stations = []
                                for result in station_results:
                                    stations.append({
                                        "id": result.get("id", ""),
                                        "name": result.get("name", ""),
                                        "coordinates": result.get("coordinates", {"lat": 0, "lon": 0})
                                    })
                                
                                logger.info(f"Found {len(stations)} stations via direct API search")
                            else:
                                return {"error": f"No stations matching '{station_name}' found in {city_name}"}
            else:
                return {"error": "Either city_name or station_name or station_id must be provided"}
        
        if not stations:
            return {"error": "No stations found with the provided criteria"}
        
        result = {
            "city": city_name,
            "stations": []
        }
        
        # Get schedule for each station
        for station in stations:
            station_id = station['id']
            station_name = station['name']
            
            logger.info(f"Getting schedule for station: {station_name} (ID: {station_id})")
            
            try:
                # Get departures
                departures = sncf_api.stations.get_departures(
                    station_id=station_id,
                    count=count,
                    datetime=datetime,
                    duration=duration,
                    data_freshness=data_freshness
                )
                
                # Get arrivals
                arrivals = sncf_api.stations.get_arrivals(
                    station_id=station_id,
                    count=count,
                    datetime=datetime,
                    duration=duration,
                    data_freshness=data_freshness
                )
                
                # Format times for better readability
                for departure in departures:
                    if 'departure_time' in departure and departure['departure_time']:
                        # Convert YYYYMMDDTHHMMSS to HH:MM:SS
                        time_str = departure['departure_time']
                        if len(time_str) >= 15:
                            departure['formatted_time'] = f"{time_str[9:11]}:{time_str[11:13]}:{time_str[13:15]}"
                
                for arrival in arrivals:
                    if 'arrival_time' in arrival and arrival['arrival_time']:
                        # Convert YYYYMMDDTHHMMSS to HH:MM:SS
                        time_str = arrival['arrival_time']
                        if len(time_str) >= 15:
                            arrival['formatted_time'] = f"{time_str[9:11]}:{time_str[11:13]}:{time_str[13:15]}"
                
                # Get coordinates from the right field
                coordinates = station.get('coordinates', station.get('coord', {"lat": 0, "lon": 0}))
                
                station_info = {
                    "id": station_id,
                    "name": station_name,
                    "coordinates": coordinates,
                    "departures": departures,
                    "arrivals": arrivals
                }
                
                result["stations"].append(station_info)
                
            except Exception as e:
                logger.error(f"Error getting schedule for station {station_name}: {str(e)}")
                # Get coordinates from the right field
                coordinates = station.get('coordinates', station.get('coord', {"lat": 0, "lon": 0}))
                result["stations"].append({
                    "id": station_id,
                    "name": station_name,
                    "coordinates": coordinates,
                    "error": str(e)
                })
        
        return result
    except Exception as e:
        logger.exception(f"Error in get_station_schedule: {str(e)}")
        return {"error": str(e)}

@mcp.tool()
def get_station_details(
    city_name: Optional[str] = None,
    station_name: Optional[str] = None,
    station_id: Optional[str] = None,
    include_transport_types: bool = True,
    include_nearby_places: bool = True,
    nearby_distance: int = 500,
    nearby_count: int = 20,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Get comprehensive details about stations in a city or a specific station.
    
    This tool provides detailed information about stations, including:
    1. Basic station information (name, ID, coordinates)
    2. Available transport types at each station (buses, trains, rapid transit, etc.)
    3. Nearby places and stop points
    
    You can search for stations by providing either:
    1. A city name (e.g., "Grenoble")
    2. A station name (e.g., "Gare de Grenoble")
    3. Both city and station name (e.g., city="Grenoble", station="Gare de Grenoble")
    4. A direct station ID if you know it
    
    Args:
        city_name: Name of the city to search for stations
        station_name: Optional name of a specific station to filter by
        station_id: Optional direct station ID (if you know the exact ID)
        include_transport_types: Whether to include transport type analysis
        include_nearby_places: Whether to include nearby places information
        nearby_distance: Search radius in meters for nearby places
        nearby_count: Maximum number of nearby places to return
        debug: Whether to include debug information in the response
        
    Returns:
        Dictionary with comprehensive station information
    """
    logger.info(f"Getting station details for city={city_name}, station={station_name}, station_id={station_id}")
    
    # Use the global SNCF API instance
    global sncf_api
    if sncf_api is None:
        logger.error("SNCF API is not initialized")
        return {"error": "SNCF API is not initialized"}
    
    result = {
        "stations": [],
        "debug": {} if debug else None
    }
    
    # If station_id is provided, use it directly
    if station_id:
        logger.info(f"Using provided station ID: {station_id}")
        station_ids = [station_id]
    else:
        # Otherwise, search for stations based on city_name and/or station_name
        if not city_name and not station_name:
            return {"error": "You must provide at least one of: city_name, station_name, or station_id"}
        
        # Construct search query
        search_query = ""
        if city_name:
            search_query += city_name
        if station_name:
            if search_query:
                search_query += " "
            search_query += station_name
            
        logger.info(f"Searching for stations with query: '{search_query}'")
        
        # Try direct hardcoded coordinates for known cities first
        stations = []
        if city_name:
            # Hardcoded coordinates for common cities
            city_coordinates = {
                "grenoble": (45.192, 5.716),
                "paris": (48.853, 2.348),
                "marseille": (43.303, 5.380),
                "lyon": (45.760, 4.860),
                "bordeaux": (44.826, -0.556),
                "lille": (50.638, 3.072),
                "toulouse": (43.611, 1.454),
                "nice": (43.704, 7.262),
                "strasbourg": (48.585, 7.735),
                "nantes": (47.217, -1.542),
                "rennes": (48.103, -1.672)
            }
            
            normalized_city = city_name.lower().strip()
            logger.info(f"Normalized city name: '{normalized_city}'")
            logger.info(f"Available hardcoded cities: {list(city_coordinates.keys())}")
            
            if normalized_city in city_coordinates:
                lat, lon = city_coordinates[normalized_city]
                logger.info(f"Using hardcoded coordinates for {city_name}: {lat}, {lon}")
                
                try:
                    # Search for stations near these coordinates
                    logger.info(f"Searching for places nearby coordinates: {lat}, {lon}")
                    places_nearby = sncf_api.search.places_nearby(
                        lat=lat,
                        lon=lon,
                        distance=500,
                        count=5,
                        depth=1
                    )
                    
                    logger.info(f"Found {len(places_nearby)} places nearby coordinates")
                    
                    # Find the first stop_area (station)
                    for place in places_nearby:
                        if place.get("type") == "stop_area":
                            stations = [place]
                            logger.info(f"Found station using coordinates: {place.get('id', 'Unknown ID')} - {place.get('name', 'Unknown Name')}")
                            break
                except Exception as e:
                    logger.warning(f"Error using coordinates search: {str(e)}")
                    if debug:
                        result["debug"]["coordinates_search_error"] = str(e)
        
        # If no stations found with coordinates, try direct API search
        if not stations:
            try:
                # Search for stations
                places = sncf_api.search_places(search_query, count=10)
                
                # Filter for stop_area type (stations)
                stations = [place for place in places if place.get("type") == "stop_area"]
                
                if stations:
                    logger.info(f"Found {len(stations)} stations via direct search")
                else:
                    logger.info("No stations found via direct search")
                    
                if debug:
                    result["debug"]["direct_search_results"] = places
            except Exception as e:
                logger.warning(f"Error in direct search: {str(e)}")
                if debug:
                    result["debug"]["direct_search_error"] = str(e)
        
        # If still no stations, try StationFinder
        if not stations and city_name:
            logger.info("Trying fallback with StationFinder")
            try:
                station = sncf_api.find_station_by_name(city_name, station_name)
                if station and "id" in station:
                    stations = [station]
                    logger.info(f"Found station using StationFinder: {station.get('id', 'Unknown ID')}")
                else:
                    logger.info("No station found using StationFinder")
            except Exception as e:
                logger.warning(f"Error using StationFinder: {str(e)}")
                if debug:
                    result["debug"]["station_finder_error"] = str(e)
        
        if not stations:
            error_msg = f"No stations found for query: {search_query}"
            logger.error(error_msg)
            return {"error": error_msg}
            
        if debug:
            result["debug"]["filtered_stations"] = stations
            
        # Extract station IDs
        station_ids = [station.get("id") for station in stations if station.get("id")]
        
    # Process each station
    for station_id in station_ids:
        station_info = {
            "id": station_id,
            "transport_types": {},
            "nearby_places": []
        }
        
        # Get transport types if requested
        if include_transport_types:
            try:
                # Get places nearby the station to analyze transport types
                places_nearby = sncf_api.get_places_nearby_station(
                    station_id=station_id,
                    distance=nearby_distance,
                    count=nearby_count,
                    type_list=["stop_point"]
                )
                
                # Analyze transport types
                transport_types = {}
                for place in places_nearby:
                    if place.get("type") == "stop_point" and "stop_point" in place:
                        stop_point = place.get("stop_point", {})
                        
                        # Extract physical modes
                        for mode in stop_point.get("physical_modes", []):
                            mode_name = mode.get("name", "Unknown")
                            if mode_name not in transport_types:
                                transport_types[mode_name] = {
                                    "count": 0,
                                    "lines": set(),
                                    "stop_points": []
                                }
                            
                            transport_types[mode_name]["count"] += 1
                            
                            # Add stop point information
                            transport_types[mode_name]["stop_points"].append({
                                "id": place.get("id", ""),
                                "name": place.get("name", ""),
                                "distance": place.get("distance", 0),
                                "coord": place.get("coord", {})
                            })
                            
                            # Add line information
                            for line in stop_point.get("lines", []):
                                line_id = line.get("id", "")
                                if line_id:
                                    transport_types[mode_name]["lines"].add(line_id)
                
                # Convert sets to lists for JSON serialization
                for mode_name in transport_types:
                    transport_types[mode_name]["lines"] = list(transport_types[mode_name]["lines"])
                    
                station_info["transport_types"] = transport_types
                
                # Get basic station information
                for place in places_nearby:
                    if place.get("id") == station_id:
                        station_info["name"] = place.get("name", "")
                        station_info["coord"] = place.get("coord", {})
                        break
                
            except Exception as e:
                logger.exception(f"Error getting transport types for station {station_id}")
                station_info["transport_types_error"] = str(e)
        
        # Get nearby places if requested
        if include_nearby_places:
            try:
                # Get places nearby the station
                places_nearby = sncf_api.get_places_nearby_station(
                    station_id=station_id,
                    distance=nearby_distance,
                    count=nearby_count
                )
                
                # Filter out the station itself
                places_nearby = [place for place in places_nearby if place.get("id") != station_id]
                
                station_info["nearby_places"] = places_nearby
                
            except Exception as e:
                logger.exception(f"Error getting nearby places for station {station_id}")
                station_info["nearby_places_error"] = str(e)
        
        result["stations"].append(station_info)
    
    return result


# ------------------ MAIN EXECUTION ------------------ #

def main() -> None:
    """
    Main entry point for the SNCF API MCP Server.
    Initializes the API and CSV station finder, logs file details, and starts the MCP server.
    """
    global csv_station_finder, sncf_api

    args = parse_arguments()
    csv_path = resolve_csv_path(args.csv_file)
    print_file_info(csv_path)

    try:
        csv_station_finder = initialize_csv_station_finder(csv_path)
        sncf_api = initialize_sncf_api(args.api_key)
    except Exception as e:
        logger.error("Initialization failed, exiting.")
        sys.exit(1)

    try:
        cities = csv_station_finder.get_all_cities()
        logger.info(f"Available cities: {cities}")
    except Exception as e:
        logger.exception("Error during station finder debug checks")
        sys.exit(1)

    logger.info("Starting SNCF API MCP Server with CSV Station Database...")
    logger.info(f"Using CSV file: {csv_path}")
    mcp.run()


if __name__ == "__main__":
    main()
