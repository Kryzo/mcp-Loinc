from typing import Dict, Any, List, Optional
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH

class SearchAPI:
    """
    Search-related API endpoints
    """
    
    def __init__(self, client: SNCFClient):
        """
        Initialize with a SNCF API client
        """
        self.client = client
        
    def places(self, query: str, count: int = DEFAULT_COUNT) -> List[Dict[str, Any]]:
        """
        Search for places (stations, addresses, POIs)
        
        Args:
            query: The search query (e.g., "Paris", "Gare de Lyon")
            count: Maximum number of results to return
            
        Returns:
            A list of places matching the query
        """
        params = {
            "q": query,
            "count": count
        }
        
        data = self.client._make_request("places", params)
        places = []
        
        if "places" in data:
            for place in data["places"]:
                place_info = {
                    "id": place.get("id", ""),
                    "name": place.get("name", ""),
                    "type": place.get("embedded_type", ""),
                    "quality": place.get("quality", 0),
                    "coordinates": place.get("coord", {}),
                    "administrative_regions": [region.get("name", "") for region in place.get("administrative_regions", [])]
                }
                places.append(place_info)
                
        return places
        
    def places_nearby(
        self,
        lon: float,
        lat: float,
        coverage: str = "sncf",
        type_list: Optional[List[str]] = None,
        distance: int = 500,
        count: int = DEFAULT_COUNT,
        depth: int = 1,
        filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get places nearby a specific location
        
        Args:
            lon: Longitude of the location
            lat: Latitude of the location
            coverage: The coverage area
            type_list: List of types of places to return (stop_point, stop_area, etc.)
            distance: Search radius in meters
            count: Maximum number of places to return
            depth: Level of detail in the response (0-3)
            filter: Filter places by a specific field
            
        Returns:
            A list of places near the specified location
        """
        params = {
            "distance": distance,
            "count": count,
            "depth": depth
        }
        
        if type_list:
            params.update(self.client._format_list_param("type", type_list))
            
        if filter:
            params["filter"] = filter
            
        endpoint = f"coverage/{coverage}/coords/{lon};{lat}/places_nearby"
        data = self.client._make_request(endpoint, params)
        places = []
        
        if "places_nearby" in data:
            for place in data["places_nearby"]:
                place_info = {
                    "id": place.get("id", ""),
                    "name": place.get("name", ""),
                    "type": place.get("embedded_type", ""),
                    "distance": place.get("distance", 0),
                    "coord": place.get("coord", {}),
                    "administrative_regions": [region.get("name", "") for region in place.get("administrative_regions", [])]
                }
                
                if place.get("embedded_type") == "stop_point":
                    place_info["stop_point"] = {
                        "lines": [{"id": line.get("id", ""), "name": line.get("name", "")} for line in place.get("stop_point", {}).get("lines", [])]
                    }
                
                places.append(place_info)
                
        return places
