import requests
import logging
from typing import Dict, Any, Optional, List, Union
from .config import SNCF_BASE_URL

# Set up logging
logger = logging.getLogger(__name__)

class SNCFClient:
    """
    Client for the SNCF API
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the SNCF API client
        
        Args:
            api_key: Your SNCF API key
        """
        self.api_key = api_key
        self.auth = (api_key, "")  # SNCF API uses Basic Auth with key as username
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the SNCF API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as a dictionary
        """
        url = f"{SNCF_BASE_URL}{endpoint}"
        
        # Clean None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        # Log the request details
        logger.info(f"Making API request to: {url}")
        logger.info(f"Request parameters: {params}")
        
        try:
            response = requests.get(url, auth=self.auth, params=params)
            logger.info(f"Response status code: {response.status_code}")
            
            # Log response headers and content for debugging
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Error response content: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            return {"error": str(e)}
            
    def _format_list_param(self, param_name: str, values: List[str]) -> Dict[str, List[str]]:
        """
        Format list parameters for the API
        
        Args:
            param_name: Parameter name
            values: List of values
            
        Returns:
            Dictionary with formatted parameter
        """
        return {f"{param_name}[]": values}
