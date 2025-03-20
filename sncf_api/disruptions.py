from typing import Dict, Any, List, Optional
import re
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH

class DisruptionsAPI:
    """
    Disruption-related API endpoints
    """
    
    def __init__(self, client: SNCFClient):
        """
        Initialize with a SNCF API client
        """
        self.client = client
        
    def get_disruptions(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH,
        datetime: Optional[str] = None,
        forbidden_uris: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        filter: Optional[str] = None,
        tags: Optional[List[str]] = None,
        fetch_train_details: bool = True,
        station_id: Optional[str] = None,
        line_id: Optional[str] = None,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Check for current disruptions in the transport network
        
        Args:
            coverage: The coverage area
            count: Maximum number of disruptions to return
            depth: Level of detail in the response (0-3)
            datetime: Date and time in format YYYYMMDDTHHMMSS
            forbidden_uris: List of URIs to exclude from the disruptions
            since: Only disruptions valid after this date (format YYYYMMDDTHHMMSS)
            until: Only disruptions valid before this date (format YYYYMMDDTHHMMSS)
            filter: Filter disruptions by a specific field
            tags: List of tags to filter disruptions
            fetch_train_details: Whether to include detailed information about stops and schedules
            station_id: Filter disruptions affecting a specific station
            line_id: Filter disruptions affecting a specific line
            debug: Whether to include the raw response in the output
            
        Returns:
            A list of current disruptions with detailed information
        """
        params = {
            "count": count,
            "depth": depth,
            "_current_datetime": datetime
        }
        
        if forbidden_uris:
            params.update(self.client._format_list_param("forbidden_uris", forbidden_uris))
            
        if since:
            params["since"] = since
            
        if until:
            params["until"] = until
            
        if filter:
            params["filter"] = filter
            
        if tags:
            params.update(self.client._format_list_param("tags", tags))
        
        if station_id:
            params["filter"] = f"stop_point.id={station_id}"
        
        if line_id:
            params["filter"] = f"line.id={line_id}"
            
        endpoint = f"coverage/{coverage}/disruptions"
        data = self.client._make_request(endpoint, params)
        disruptions = []
        
        if "disruptions" in data:
            for disruption in data["disruptions"]:
                disruption_info = {
                    "id": disruption.get("id", ""),
                    "disruption_id": disruption.get("disruption_id", ""),
                    "status": disruption.get("status", ""),
                    "impact_id": disruption.get("impact_id", ""),
                    "cause": disruption.get("cause", ""),
                    "updated_at": disruption.get("updated_at", ""),
                    "severity": {
                        "name": disruption.get("severity", {}).get("name", ""),
                        "effect": disruption.get("severity", {}).get("effect", ""),
                        "color": disruption.get("severity", {}).get("color", ""),
                        "priority": disruption.get("severity", {}).get("priority", 0)
                    },
                    "application_periods": [],
                    "messages": [],
                }
                
                # Extract application periods
                for period in disruption.get("application_periods", []):
                    disruption_info["application_periods"].append({
                        "begin": period.get("begin", ""),
                        "end": period.get("end", "")
                    })
                
                # Extract messages
                for message in disruption.get("messages", []):
                    if "text" in message:
                        message_info = {
                            "text": message["text"],
                            "channel": {
                                "name": message.get("channel", {}).get("name", ""),
                                "types": message.get("channel", {}).get("types", [])
                            }
                        }
                        disruption_info["messages"].append(message_info)
                
                # Extract detailed information about impacted objects and stops
                impacted_objects = []
                
                for impacted_object in disruption.get("impacted_objects", []):
                    if "pt_object" in impacted_object:
                        pt_object = impacted_object["pt_object"]
                        embedded_type = pt_object.get("embedded_type", "")
                        
                        impacted_info = {
                            "id": pt_object.get("id", ""),
                            "name": pt_object.get("name", ""),
                            "type": embedded_type,
                        }
                        
                        # Add more details based on the embedded type
                        if embedded_type in pt_object:
                            impacted_info[embedded_type] = pt_object[embedded_type]
                        
                        # Add stop information if available and fetch_train_details is True
                        if fetch_train_details and "impacted_stops" in impacted_object:
                            stops_info = []
                            
                            # Track origin and destination
                            origin_stop = None
                            destination_stop = None
                            
                            for i, stop in enumerate(impacted_object.get("impacted_stops", [])):
                                stop_info = {
                                    "stop_name": stop.get("stop_point", {}).get("name", ""),
                                    "stop_id": stop.get("stop_point", {}).get("id", ""),
                                    "city": self._extract_city_from_label(stop.get("stop_point", {}).get("label", "")),
                                    "coordinates": {
                                        "lon": stop.get("stop_point", {}).get("coord", {}).get("lon", ""),
                                        "lat": stop.get("stop_point", {}).get("coord", {}).get("lat", "")
                                    },
                                    "base_arrival_time": self._format_time(stop.get("base_arrival_time", "")),
                                    "base_departure_time": self._format_time(stop.get("base_departure_time", "")),
                                    "amended_arrival_time": self._format_time(stop.get("amended_arrival_time", "")),
                                    "amended_departure_time": self._format_time(stop.get("amended_departure_time", "")),
                                    "cause": stop.get("cause", ""),
                                    "stop_time_effect": stop.get("stop_time_effect", ""),
                                    "arrival_status": stop.get("arrival_status", ""),
                                    "departure_status": stop.get("departure_status", ""),
                                    "is_detour": stop.get("is_detour", False)
                                }
                                
                                # Track first stop as origin
                                if i == 0:
                                    origin_stop = stop_info
                                
                                # Update destination with each stop, so the last one becomes the final destination
                                destination_stop = stop_info
                                
                                stops_info.append(stop_info)
                            
                            impacted_info["stops"] = stops_info
                            
                            # Add origin and destination info for easier access
                            if origin_stop:
                                impacted_info["origin"] = {
                                    "stop_name": origin_stop["stop_name"],
                                    "city": origin_stop["city"],
                                    "base_departure_time": origin_stop["base_departure_time"],
                                    "amended_departure_time": origin_stop["amended_departure_time"]
                                }
                            
                            if destination_stop:
                                impacted_info["destination"] = {
                                    "stop_name": destination_stop["stop_name"],
                                    "city": destination_stop["city"],
                                    "base_arrival_time": destination_stop["base_arrival_time"],
                                    "amended_arrival_time": destination_stop["amended_arrival_time"]
                                }
                            
                            # Calculate disruption effects summary
                            impacted_info["disruption_effects"] = self._calculate_disruption_effects(stops_info)
                        
                        impacted_objects.append(impacted_info)
                    
                    disruption_info["impacted_objects"] = impacted_objects
                
                # Add raw data if debug is True
                if debug:
                    disruption_info["raw_data"] = disruption
                
                disruptions.append(disruption_info)
                
        return disruptions

    def _extract_city_from_label(self, label: str) -> str:
        """
        Extract city name from a label in format "Station Name (City Name)"
        
        Args:
            label: The label string to parse
            
        Returns:
            The extracted city name or empty string if not found
        """
        if not label:
            return ""
        
        # Try to extract city from parentheses
        match = re.search(r'\((.*?)\)', label)
        if match:
            return match.group(1)
        
        return ""

    def _format_time(self, time_str: str) -> str:
        """
        Format time string from HHMMSS to HH:MM:SS
        
        Args:
            time_str: Time string in format HHMMSS
            
        Returns:
            Formatted time string HH:MM:SS or empty string if invalid
        """
        if not time_str or len(time_str) < 6:
            return ""
        
        try:
            # Extract hours, minutes, seconds
            hours = time_str[:2]
            minutes = time_str[2:4]
            seconds = time_str[4:6]
            
            return f"{hours}:{minutes}:{seconds}"
        except Exception:
            return time_str

    def _calculate_disruption_effects(self, stops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate disruption effects summary from stop information
        
        Args:
            stops: List of stop information dictionaries
            
        Returns:
            Dictionary with disruption effect summary
        """
        effects = {
            "has_cancellations": False,
            "has_delays": False,
            "has_added_stops": False,
            "has_detours": False,
            "total_delay_minutes": 0,
            "affected_stops": []
        }
        
        for stop in stops:
            # Check for cancellations
            if stop["stop_time_effect"] == "deleted":
                effects["has_cancellations"] = True
                effects["affected_stops"].append({
                    "stop_name": stop["stop_name"],
                    "city": stop["city"],
                    "effect": "cancelled"
                })
            
            # Check for added stops
            elif stop["stop_time_effect"] == "added":
                effects["has_added_stops"] = True
                effects["affected_stops"].append({
                    "stop_name": stop["stop_name"],
                    "city": stop["city"],
                    "effect": "added"
                })
            
            # Check for delays
            if stop["base_arrival_time"] and stop["amended_arrival_time"] and stop["base_arrival_time"] != stop["amended_arrival_time"]:
                effects["has_delays"] = True
                
                # Calculate delay in minutes
                base_arr = stop["base_arrival_time"].replace(":", "")
                amended_arr = stop["amended_arrival_time"].replace(":", "")
                
                try:
                    # Very simplified delay calculation (assumes same day)
                    base_minutes = int(base_arr[:2]) * 60 + int(base_arr[2:4])
                    amended_minutes = int(amended_arr[:2]) * 60 + int(amended_arr[2:4])
                    delay = amended_minutes - base_minutes
                    
                    # Handle negative delay (possible for early arrivals)
                    if delay > 0:
                        effects["total_delay_minutes"] += delay
                    
                        effects["affected_stops"].append({
                            "stop_name": stop["stop_name"],
                            "city": stop["city"],
                            "effect": "delayed",
                            "delay_minutes": delay
                        })
                except Exception:
                    pass
            
            # Check for detours
            if stop["is_detour"]:
                effects["has_detours"] = True
                effects["affected_stops"].append({
                    "stop_name": stop["stop_name"],
                    "city": stop["city"],
                    "effect": "detour"
                })
        
        return effects