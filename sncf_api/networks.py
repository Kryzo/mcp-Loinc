from typing import Dict, Any, List, Optional
from .client import SNCFClient
from .config import DEFAULT_COUNT, DEFAULT_DEPTH

class NetworksAPI:
    """
    Network-related API endpoints
    """
    
    def __init__(self, client: SNCFClient):
        """
        Initialize with a SNCF API client
        """
        self.client = client
        
    def get_regions(self) -> List[Dict[str, Any]]:
        """
        Get all available regions (coverage) from the SNCF API
        
        Returns:
            A list of available regions with their IDs and details
        """
        data = self.client._make_request("coverage")
        regions = []
        
        if "regions" in data:
            for region in data["regions"]:
                region_info = {
                    "id": region.get("id", ""),
                    "name": region.get("name", ""),
                    "status": region.get("status", ""),
                    "shape": region.get("shape", ""),
                }
                regions.append(region_info)
                
        return regions
        
    def get_lines(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH,
        filter: Optional[str] = None,
        forbidden_uris: Optional[List[str]] = None,
        start_page: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get transport lines
        
        Args:
            coverage: The coverage area
            count: Maximum number of lines to return
            depth: Level of detail in the response (0-3)
            filter: Filter lines by a specific field
            forbidden_uris: List of URIs to exclude from the lines
            start_page: Page number for pagination
            
        Returns:
            A list of transport lines
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
            
        endpoint = f"coverage/{coverage}/lines"
        data = self.client._make_request(endpoint, params)
        lines = []
        
        if "lines" in data:
            for line in data["lines"]:
                line_info = {
                    "id": line.get("id", ""),
                    "name": line.get("name", ""),
                    "code": line.get("code", ""),
                    "color": line.get("color", ""),
                    "text_color": line.get("text_color", ""),
                    "commercial_mode": {
                        "id": line.get("commercial_mode", {}).get("id", ""),
                        "name": line.get("commercial_mode", {}).get("name", "")
                    },
                    "network": {
                        "id": line.get("network", {}).get("id", ""),
                        "name": line.get("network", {}).get("name", "")
                    }
                }
                
                # Add routes if available with depth
                if "routes" in line:
                    line_info["routes"] = [{"id": route.get("id", ""), "name": route.get("name", "")} for route in line.get("routes", [])]
                
                lines.append(line_info)
                
        return lines
        
    def get_commercial_modes(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH
    ) -> List[Dict[str, Any]]:
        """
        Get commercial modes
        
        Args:
            coverage: The coverage area
            count: Maximum number of commercial modes to return
            depth: Level of detail in the response (0-3)
            
        Returns:
            A list of commercial modes
        """
        params = {
            "count": count,
            "depth": depth
        }
            
        endpoint = f"coverage/{coverage}/commercial_modes"
        data = self.client._make_request(endpoint, params)
        modes = []
        
        if "commercial_modes" in data:
            for mode in data["commercial_modes"]:
                mode_info = {
                    "id": mode.get("id", ""),
                    "name": mode.get("name", "")
                }
                modes.append(mode_info)
                
        return modes
        
    def get_physical_modes(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH
    ) -> List[Dict[str, Any]]:
        """
        Get physical modes
        
        Args:
            coverage: The coverage area
            count: Maximum number of physical modes to return
            depth: Level of detail in the response (0-3)
            
        Returns:
            A list of physical modes
        """
        params = {
            "count": count,
            "depth": depth
        }
            
        endpoint = f"coverage/{coverage}/physical_modes"
        data = self.client._make_request(endpoint, params)
        modes = []
        
        if "physical_modes" in data:
            for mode in data["physical_modes"]:
                mode_info = {
                    "id": mode.get("id", ""),
                    "name": mode.get("name", "")
                }
                modes.append(mode_info)
                
        return modes
        
    def get_networks(
        self,
        coverage: str = "sncf",
        count: int = DEFAULT_COUNT,
        depth: int = DEFAULT_DEPTH,
        filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transit networks
        
        Args:
            coverage: The coverage area
            count: Maximum number of networks to return
            depth: Level of detail in the response (0-3)
            filter: Filter networks by a specific field
            
        Returns:
            A list of transit networks
        """
        params = {
            "count": count,
            "depth": depth
        }
        
        if filter:
            params["filter"] = filter
            
        endpoint = f"coverage/{coverage}/networks"
        data = self.client._make_request(endpoint, params)
        networks = []
        
        if "networks" in data:
            for network in data["networks"]:
                network_info = {
                    "id": network.get("id", ""),
                    "name": network.get("name", ""),
                    "codes": [{"type": code.get("type", ""), "value": code.get("value", "")} for code in network.get("codes", [])]
                }
                networks.append(network_info)
                
        return networks
