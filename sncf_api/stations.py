from typing import Dict, Any, List, Optional
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH, DEFAULT_DATA_FRESHNESS

class StationsAPI:
    """
    Station-related API endpoints
    """
    
    def __init__(self, client: SNCFClient):
        """
        Initialize with a SNCF API client
        """
        self.client = client
        
    def get_departures(
        self,
        station_id: str,
        coverage: str = "sncf",
        count: int = 5,
        datetime: Optional[str] = None,
        duration: Optional[int] = None,
        depth: int = DEFAULT_DEPTH,
        data_freshness: str = DEFAULT_DATA_FRESHNESS,
        forbidden_uris: Optional[List[str]] = None,
        show_codes: bool = False,
        from_datetime: Optional[str] = None,
        until_datetime: Optional[str] = None,
        direction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get next departures from a station
        
        Args:
            station_id: The ID of the station (stop_area)
            coverage: The coverage region
            count: Maximum number of departures to return
            datetime: Date and time in format YYYYMMDDTHHMMSS
            duration: Duration in seconds to search for departures after datetime
            depth: Level of detail in the response (0-3)
            data_freshness: Data freshness level ("realtime", "base_schedule")
            forbidden_uris: List of URIs to exclude from the departures
            show_codes: Whether to show the codes for the objects in the response
            from_datetime: Start datetime for the search in format YYYYMMDDTHHMMSS
            until_datetime: End datetime for the search in format YYYYMMDDTHHMMSS
            direction_type: Filter by direction type
            
        Returns:
            A list of upcoming departures
        """
        params = {
            "count": count,
            "depth": depth,
            "data_freshness": data_freshness,
            "show_codes": show_codes,
            "_current_datetime": datetime
        }
        
        if duration:
            params["duration"] = duration
            
        if from_datetime:
            params["from_datetime"] = from_datetime
            
        if until_datetime:
            params["until_datetime"] = until_datetime
            
        if direction_type:
            params["direction_type"] = direction_type
            
        if forbidden_uris:
            params.update(self.client._format_list_param("forbidden_uris", forbidden_uris))
            
        endpoint = f"coverage/{coverage}/stop_areas/{station_id}/departures"
        data = self.client._make_request(endpoint, params)
        departures = []
        
        if "departures" in data:
            for departure in data["departures"]:
                display_info = departure.get("display_informations", {})
                stop_date_time = departure.get("stop_date_time", {})
                route = departure.get("route", {})
                
                departure_info = {
                    "line": display_info.get("code", ""),
                    "direction": display_info.get("direction", ""),
                    "network": display_info.get("network", ""),
                    "commercial_mode": display_info.get("commercial_mode", ""),
                    "physical_mode": display_info.get("physical_mode", ""),
                    "headsign": display_info.get("headsign", ""),
                    "label": display_info.get("label", ""),
                    "base_departure_time": stop_date_time.get("base_departure_date_time", ""),
                    "departure_time": stop_date_time.get("departure_date_time", ""),
                    "route_name": route.get("name", ""),
                    "stop_point": departure.get("stop_point", {}).get("name", "")
                }
                departures.append(departure_info)
                
        return departures
        
    def get_arrivals(
        self,
        station_id: str,
        coverage: str = "sncf",
        count: int = 5,
        datetime: Optional[str] = None,
        duration: Optional[int] = None,
        depth: int = DEFAULT_DEPTH,
        data_freshness: str = DEFAULT_DATA_FRESHNESS,
        forbidden_uris: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get next arrivals at a station
        
        Args:
            station_id: The ID of the station (stop_area)
            coverage: The coverage region
            count: Maximum number of arrivals to return
            datetime: Date and time in format YYYYMMDDTHHMMSS
            duration: Duration in seconds to search for arrivals after datetime
            depth: Level of detail in the response (0-3)
            data_freshness: Data freshness level ("realtime", "base_schedule")
            forbidden_uris: List of URIs to exclude from the arrivals
            
        Returns:
            A list of upcoming arrivals
        """
        params = {
            "count": count,
            "depth": depth,
            "data_freshness": data_freshness,
            "_current_datetime": datetime
        }
        
        if duration:
            params["duration"] = duration
            
        if forbidden_uris:
            params.update(self.client._format_list_param("forbidden_uris", forbidden_uris))
            
        endpoint = f"coverage/{coverage}/stop_areas/{station_id}/arrivals"
        data = self.client._make_request(endpoint, params)
        arrivals = []
        
        if "arrivals" in data:
            for arrival in data["arrivals"]:
                display_info = arrival.get("display_informations", {})
                stop_date_time = arrival.get("stop_date_time", {})
                
                arrival_info = {
                    "line": display_info.get("code", ""),
                    "direction": display_info.get("direction", ""),
                    "network": display_info.get("network", ""),
                    "commercial_mode": display_info.get("commercial_mode", ""),
                    "physical_mode": display_info.get("physical_mode", ""),
                    "headsign": display_info.get("headsign", ""),
                    "label": display_info.get("label", ""),
                    "base_arrival_time": stop_date_time.get("base_arrival_date_time", ""),
                    "arrival_time": stop_date_time.get("arrival_date_time", ""),
                    "stop_point": arrival.get("stop_point", {}).get("name", "")
                }
                arrivals.append(arrival_info)
                
        return arrivals
        
    def get_stop_points(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH,
        filter: Optional[str] = None,
        forbidden_uris: Optional[List[str]] = None,
        distance: Optional[int] = None,
        start_page: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get stop points
        
        Args:
            coverage: The coverage area
            count: Maximum number of stop points to return
            depth: Level of detail in the response (0-3)
            filter: Filter stop points by a specific field
            forbidden_uris: List of URIs to exclude from the stop points
            distance: Search radius in meters
            start_page: Page number for pagination
            
        Returns:
            A list of stop points
        """
        params = {
            "count": count,
            "depth": depth,
            "start_page": start_page
        }
        
        if filter:
            params["filter"] = filter
            
        if forbidden_uris:
            params.update(self.client._format_list_param("forbidden_uris", forbidden_uris))
            
        if distance:
            params["distance"] = distance
            
        endpoint = f"coverage/{coverage}/stop_points"
        data = self.client._make_request(endpoint, params)
        stop_points = []
        
        if "stop_points" in data:
            for stop_point in data["stop_points"]:
                stop_point_info = {
                    "id": stop_point.get("id", ""),
                    "name": stop_point.get("name", ""),
                    "coord": stop_point.get("coord", {}),
                    "label": stop_point.get("label", ""),
                    "codes": [{"type": code.get("type", ""), "value": code.get("value", "")} for code in stop_point.get("codes", [])],
                    "administrative_regions": [{"id": region.get("id", ""), "name": region.get("name", "")} for region in stop_point.get("administrative_regions", [])],
                    "physical_modes": [{"id": mode.get("id", ""), "name": mode.get("name", "")} for mode in stop_point.get("physical_modes", [])]
                }
                stop_points.append(stop_point_info)
                
        return stop_points
        
    def get_places_nearby_station(
        self,
        station_id: str,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH,
        distance: int = 500,
        type_list: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get places nearby a specific station
        
        Args:
            station_id: The ID of the station (stop_area)
            coverage: The coverage area
            count: Maximum number of places to return
            depth: Level of detail in the response (0-3)
            distance: Search radius in meters
            type_list: List of types of places to return (stop_point, stop_area, etc.)
            
        Returns:
            A list of places near the specified station
        """
        params = {
            "distance": distance,
            "count": count,
            "depth": depth
        }
        
        if type_list:
            params.update(self.client._format_list_param("type", type_list))
            
        endpoint = f"coverage/{coverage}/stop_areas/{station_id}/places_nearby"
        data = self.client._make_request(endpoint, params)
        places = []
        
        if "places_nearby" in data:
            for place in data["places_nearby"]:
                place_info = {
                    "id": place.get("id", ""),
                    "name": place.get("name", ""),
                    "type": place.get("embedded_type", ""),
                    "distance": place.get("distance", 0),
                    "coord": place.get("coord", {})
                }
                
                # Add type-specific information
                if place.get("embedded_type") == "stop_point":
                    stop_point = place.get("stop_point", {})
                    
                    # Extract physical modes if available
                    physical_modes = []
                    for mode in stop_point.get("physical_modes", []):
                        physical_modes.append({
                            "id": mode.get("id", ""),
                            "name": mode.get("name", "")
                        })
                    
                    # Extract lines if available
                    lines = []
                    for line in stop_point.get("lines", []):
                        lines.append({
                            "id": line.get("id", ""),
                            "name": line.get("name", ""),
                            "code": line.get("code", ""),
                            "color": line.get("color", ""),
                            "text_color": line.get("text_color", "")
                        })
                    
                    place_info["stop_point"] = {
                        "physical_modes": physical_modes,
                        "lines": lines,
                        "equipments": stop_point.get("equipments", [])
                    }
                
                places.append(place_info)
                
        return places
