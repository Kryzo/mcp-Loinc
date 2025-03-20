from typing import Dict, Any, List, Optional
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH, DEFAULT_DATA_FRESHNESS

class JourneyAPI:
    """
    Journey-related API endpoints
    """
    
    def __init__(self, client: SNCFClient):
        """
        Initialize with a SNCF API client
        """
        self.client = client
        
    def plan_journey(
        self,
        from_place: str, 
        to_place: str, 
        datetime: Optional[str] = None,
        datetime_represents: str = "departure",
        coverage: str = "sncf",
        count: int = 3,
        min_nb_journeys: Optional[int] = None,
        max_nb_journeys: Optional[int] = None,
        first_section_mode: Optional[List[str]] = None,
        last_section_mode: Optional[List[str]] = None,
        forbidden_uris: Optional[List[str]] = None,
        depth: int = DEFAULT_DEPTH,
        direct_path: str = "indifferent",
        data_freshness: str = DEFAULT_DATA_FRESHNESS
    ) -> Dict[str, Any]:
        """
        Plan a journey between two places
        
        Args:
            from_place: The starting point (can be a place ID or coordinates)
            to_place: The destination (can be a place ID or coordinates)
            datetime: Date and time in format YYYYMMDDTHHMMSS (default: now)
            datetime_represents: Either "departure" or "arrival" (default: departure)
            coverage: The coverage region
            count: Maximum number of journeys to return
            min_nb_journeys: Minimum number of journeys to return
            max_nb_journeys: Maximum number of journeys to return
            first_section_mode: List of modes for the first section of the journey
            last_section_mode: List of modes for the last section of the journey
            forbidden_uris: List of URIs to exclude from the journey
            depth: Level of detail in the response (0-3)
            direct_path: Whether to return direct paths ("indifferent", "only", "none")
            data_freshness: Data freshness level ("realtime", "base_schedule")
            
        Returns:
            Journey information including sections, duration, etc.
        """
        params = {
            "from": from_place,
            "to": to_place,
            "datetime_represents": datetime_represents,
            "count": count,
            "depth": depth,
            "direct_path": direct_path,
            "data_freshness": data_freshness
        }
        
        if datetime:
            params["datetime"] = datetime
        
        if min_nb_journeys:
            params["min_nb_journeys"] = min_nb_journeys
            
        if max_nb_journeys:
            params["max_nb_journeys"] = max_nb_journeys
        
        if first_section_mode:
            params.update(self.client._format_list_param("first_section_mode", first_section_mode))
            
        if last_section_mode:
            params.update(self.client._format_list_param("last_section_mode", last_section_mode))
            
        if forbidden_uris:
            params.update(self.client._format_list_param("forbidden_uris", forbidden_uris))
            
        endpoint = f"coverage/{coverage}/journeys"
        data = self.client._make_request(endpoint, params)
        
        if "journeys" in data and data["journeys"]:
            journeys = []
            
            for journey in data["journeys"]:
                journey_info = {
                    "departure_time": journey.get("departure_date_time", ""),
                    "arrival_time": journey.get("arrival_date_time", ""),
                    "duration": journey.get("duration", 0),
                    "co2_emission": journey.get("co2_emission", {}).get("value", 0),
                    "nb_transfers": journey.get("nb_transfers", 0),
                    "status": journey.get("status", ""),
                    "type": journey.get("type", ""),
                    "sections": []
                }
                
                for section in journey.get("sections", []):
                    section_info = {
                        "type": section.get("type", ""),
                        "mode": section.get("mode", ""),
                        "duration": section.get("duration", 0),
                        "from": section.get("from", {}).get("name", ""),
                        "to": section.get("to", {}).get("name", "")
                    }
                    
                    if section.get("type") == "public_transport":
                        display_info = section.get("display_informations", {})
                        section_info["line"] = display_info.get("code", "")
                        section_info["network"] = display_info.get("network", "")
                        section_info["direction"] = display_info.get("direction", "")
                        section_info["commercial_mode"] = display_info.get("commercial_mode", "")
                        section_info["physical_mode"] = display_info.get("physical_mode", "")
                        
                    journey_info["sections"].append(section_info)
                
                journeys.append(journey_info)
                
            return {"journeys": journeys}
        else:
            return {"error": "No journey found"}
