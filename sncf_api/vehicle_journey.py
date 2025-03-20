from typing import Dict, Any, List, Optional
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH, DEFAULT_DATA_FRESHNESS
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VehicleJourneyAPI:
    """API for accessing vehicle journey information from the SNCF API."""
    
    def __init__(self, client):
        """Initialize the VehicleJourneyAPI with an API client."""
        self.client = client
    
    def get_vehicle_journey(self, trip_id, coverage="sncf", data_freshness="realtime"):
        """
        Get a vehicle journey by its trip ID.
        
        Args:
            trip_id: The ID of the trip to get the vehicle journey for
            coverage: The coverage area to use
            data_freshness: The freshness of the data to use (base_schedule, realtime)
            
        Returns:
            The vehicle journey data
        """
        # According to the API documentation, vehicle journeys are accessed through trip IDs
        url = f"/coverage/{coverage}/trips/{trip_id}/vehicle_journeys"
        params = {
            "data_freshness": data_freshness
        }
        
        try:
            response = self.client._make_request(url, params=params)
            
            if "vehicle_journeys" in response and response["vehicle_journeys"]:
                return response["vehicle_journeys"][0]
        except Exception as e:
            logger.error(f"Error getting vehicle journey for trip {trip_id}: {str(e)}")
        
        return None
    
    def search_vehicle_journeys(self, coverage="sncf", count=5, depth=2, data_freshness="realtime", 
                               since=None, until=None, **kwargs):
        """
        Search for vehicle journeys.
        
        Args:
            coverage: The coverage area to use
            count: The maximum number of results to return
            depth: The depth of the response
            data_freshness: The freshness of the data to use (base_schedule, realtime)
            since: Only return vehicle journeys valid after this date (format YYYYMMDDTHHMMSS)
            until: Only return vehicle journeys valid before this date (format YYYYMMDDTHHMMSS)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            A list of vehicle journeys
        """
        url = f"/coverage/{coverage}/vehicle_journeys"
        
        params = {
            "count": count,
            "depth": depth,
            "data_freshness": data_freshness
        }
        
        if since:
            params["since"] = since
        
        if until:
            params["until"] = until
        
        # Add any additional parameters
        params.update(kwargs)
        
        try:
            response = self.client._make_request(url, params=params)
            
            if "vehicle_journeys" in response:
                return response["vehicle_journeys"]
        except Exception as e:
            logger.error(f"Error searching for vehicle journeys: {str(e)}")
        
        return []
    
    def search_by_train_number(self, train_number, coverage="sncf", date=None, count=3, depth=2):
        """
        Search for vehicle journeys by train number.
        
        Args:
            train_number: The train number to search for
            coverage: The coverage area to use
            date: The date to search for (format YYYYMMDD)
            count: The maximum number of results to return
            depth: The depth of the response
            
        Returns:
            A list of vehicle journeys
        """
        # Try multiple search strategies to find the train
        trips = []
        
        # Strategy 1: Search using pt_objects endpoint with allowed types
        trips.extend(self._search_by_pt_objects(train_number, coverage, date, count, depth))
        
        # Strategy 2: Search for lines that might match the train number
        if not trips:
            trips.extend(self._search_by_line(train_number, coverage, date, count, depth))
        
        # Strategy 3: Search for stop areas that might have this train
        if not trips:
            trips.extend(self._search_by_stop_areas(train_number, coverage, date, count, depth))
        
        return trips
    
    def _search_by_pt_objects(self, train_number, coverage="sncf", date=None, count=3, depth=2):
        """Search for a train using the pt_objects endpoint with allowed types."""
        url = f"/coverage/{coverage}/pt_objects"
        
        # Try different query formats
        queries = [
            f"Train {train_number}",
            f"{train_number}",
            f"TGV {train_number}",
            f"TER {train_number}",
            f"INTERCITÉS {train_number}"
        ]
        
        # The API only allows certain types for pt_objects
        params = {
            "count": count,
            "depth": depth,
            "type[]": ["line", "route", "stop_area", "stop_point"]
        }
        
        # Add date range if provided
        if date:
            if len(date) == 8:  # Format YYYYMMDD
                since = f"{date}T000000"
                until = f"{date}T235959"
                params["since"] = since
                params["until"] = until
        
        trips = []
        for query in queries:
            try:
                params["q"] = query
                response = self.client._make_request(url, params=params)
                
                # Extract potential matches from the response
                if "pt_objects" in response:
                    for obj in response["pt_objects"]:
                        # If we find a line, check its vehicle journeys
                        if obj.get("embedded_type") == "line":
                            line = obj.get("line", {})
                            line_id = line.get("id")
                            
                            if line_id:
                                # Get vehicle journeys for this line
                                line_trips = self._get_vehicle_journeys_for_line(line_id, coverage, date, count, depth)
                                trips.extend(line_trips)
                        
                        # If we find a route, check its vehicle journeys
                        elif obj.get("embedded_type") == "route":
                            route = obj.get("route", {})
                            route_id = route.get("id")
                            
                            if route_id:
                                # Get vehicle journeys for this route
                                route_trips = self._get_vehicle_journeys_for_route(route_id, coverage, date, count, depth)
                                trips.extend(route_trips)
                
                if trips:
                    break  # Stop trying different queries if we found results
            except Exception as e:
                logger.warning(f"Error searching for train {train_number} with query '{query}': {str(e)}")
        
        return trips
    
    def _get_vehicle_journeys_for_line(self, line_id, coverage="sncf", date=None, count=3, depth=2):
        """Get vehicle journeys for a specific line."""
        url = f"/coverage/{coverage}/lines/{line_id}/vehicle_journeys"
        
        params = {
            "count": count,
            "depth": depth
        }
        
        # Add date range if provided
        if date:
            if len(date) == 8:  # Format YYYYMMDD
                since = f"{date}T000000"
                until = f"{date}T235959"
                params["since"] = since
                params["until"] = until
        
        try:
            response = self.client._make_request(url, params=params)
            
            if "vehicle_journeys" in response:
                return response["vehicle_journeys"]
        except Exception as e:
            logger.warning(f"Error getting vehicle journeys for line {line_id}: {str(e)}")
        
        return []
    
    def _get_vehicle_journeys_for_route(self, route_id, coverage="sncf", date=None, count=3, depth=2):
        """Get vehicle journeys for a specific route."""
        url = f"/coverage/{coverage}/routes/{route_id}/vehicle_journeys"
        
        params = {
            "count": count,
            "depth": depth
        }
        
        # Add date range if provided
        if date:
            if len(date) == 8:  # Format YYYYMMDD
                since = f"{date}T000000"
                until = f"{date}T235959"
                params["since"] = since
                params["until"] = until
        
        try:
            response = self.client._make_request(url, params=params)
            
            if "vehicle_journeys" in response:
                return response["vehicle_journeys"]
        except Exception as e:
            logger.warning(f"Error getting vehicle journeys for route {route_id}: {str(e)}")
        
        return []
    
    def _search_by_line(self, train_number, coverage="sncf", date=None, count=3, depth=2):
        """Search for lines that might match the train number."""
        url = f"/coverage/{coverage}/lines"
        
        params = {
            "count": count,
            "depth": depth,
            "filter": f"line.code={train_number}"  # Try using the train number as a line code
        }
        
        try:
            response = self.client._make_request(url, params=params)
            
            trips = []
            if "lines" in response and response["lines"]:
                for line in response["lines"]:
                    line_id = line.get("id")
                    
                    if line_id:
                        # Get vehicle journeys for this line
                        line_trips = self._get_vehicle_journeys_for_line(line_id, coverage, date, count, depth)
                        trips.extend(line_trips)
            
            return trips
        except Exception as e:
            logger.warning(f"Error searching for line with code {train_number}: {str(e)}")
        
        return []
    
    def _search_by_stop_areas(self, train_number, coverage="sncf", date=None, count=3, depth=2):
        """Search for stop areas that might have this train."""
        # This is a fallback method that searches for vehicle journeys at major stations
        # We'll use a list of common major stations in France
        major_stations = [
            "stop_area:SNCF:87391003",  # Paris Gare du Nord
            "stop_area:SNCF:87686006",  # Paris Gare de Lyon
            "stop_area:SNCF:87547000",  # Paris Montparnasse
            "stop_area:SNCF:87271007",  # Paris Est
            "stop_area:SNCF:87113001",  # Paris Austerlitz
            "stop_area:SNCF:87722025",  # Marseille St-Charles
            "stop_area:SNCF:87171009",  # Lyon Part-Dieu
            "stop_area:SNCF:87223263",  # Lille Flandres
        ]
        
        trips = []
        
        # Try to find vehicle journeys at major stations
        for station_id in major_stations:
            try:
                url = f"/coverage/{coverage}/stop_areas/{station_id}/vehicle_journeys"
                
                params = {
                    "count": count,
                    "depth": depth
                }
                
                # Add date range if provided
                if date:
                    if len(date) == 8:  # Format YYYYMMDD
                        since = f"{date}T000000"
                        until = f"{date}T235959"
                        params["since"] = since
                        params["until"] = until
                
                response = self.client._make_request(url, params=params)
                
                if "vehicle_journeys" in response:
                    # Filter vehicle journeys that might match the train number
                    for journey in response["vehicle_journeys"]:
                        # Check if the train number appears in the journey name or headsign
                        journey_name = journey.get("name", "")
                        headsign = journey.get("headsign", "")
                        
                        if train_number in journey_name or train_number in headsign:
                            trips.append(journey)
                
                if len(trips) >= count:
                    break  # Stop searching if we found enough results
            except Exception as e:
                logger.warning(f"Error searching for train {train_number} at station {station_id}: {str(e)}")
        
        return trips
    
    def search_by_line_code(self, line_code, coverage="sncf", date=None, count=3, depth=2):
        """
        Search for vehicle journeys by line code.
        
        Args:
            line_code: The line code to search for
            coverage: The coverage area to use
            date: The date to search for (format YYYYMMDD)
            count: The maximum number of results to return
            depth: The depth of the response
            
        Returns:
            A list of vehicle journeys
        """
        url = f"/coverage/{coverage}/lines"
        
        # First, find the line by its code
        params = {
            "count": 1,
            "depth": 1,
            "filter": f"line.code={line_code}"
        }
        
        try:
            response = self.client._make_request(url, params=params)
            
            if "lines" in response and response["lines"]:
                line = response["lines"][0]
                line_id = line.get("id")
                
                if line_id:
                    # Now get vehicle journeys for this line
                    return self._get_vehicle_journeys_for_line(line_id, coverage, date, count, depth)
        except Exception as e:
            logger.warning(f"Error searching for line {line_code}: {str(e)}")
        
        return []
