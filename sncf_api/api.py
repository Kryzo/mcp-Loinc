from typing import Dict, Any, List, Optional, Union
from .client import SNCFClient
from .search import SearchAPI
from .journey import JourneyAPI
from .stations import StationsAPI
from .disruptions import DisruptionsAPI
from .networks import NetworksAPI
from .station_finder import StationFinder
from .vehicle_journey import VehicleJourneyAPI

class SNCFAPI:
    """
    Main SNCF API class that combines all API endpoints
    """
    
    def __init__(
        self,
        api_key: str,
        client: Optional[SNCFClient] = None
    ) -> None:
        """
        Initialize the SNCF API client.
        
        Args:
            api_key: The API key to use for authentication
            client: An optional client to use for making requests
        """
        self.client = client or SNCFClient(api_key=api_key)
        self.search = SearchAPI(self.client)
        self.journey = JourneyAPI(self.client)
        self.stations = StationsAPI(self.client)
        self.disruptions = DisruptionsAPI(self.client)
        self.networks = NetworksAPI(self.client)
        self.station_finder = StationFinder(self)
        self.vehicle_journey = VehicleJourneyAPI(self.client)
        
    def get_regions(self) -> List[Dict[str, Any]]:
        """
        Get all available regions (coverage)
        """
        return self.networks.get_regions()
        
    def search_places(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Search for places (stations, addresses, POIs)
        """
        return self.search.places(query, count)
        
    def plan_journey(
        self,
        from_place: str, 
        to_place: str, 
        datetime: Optional[str] = None,
        datetime_represents: str = "departure",
        coverage: str = "sncf",
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Plan a journey between two places
        """
        return self.journey.plan_journey(
            from_place=from_place,
            to_place=to_place,
            datetime=datetime,
            datetime_represents=datetime_represents,
            coverage=coverage,
            count=count
        )
        
    def get_departures(
        self,
        station_id: str,
        coverage: str = "sncf",
        count: int = 5,
        datetime: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get next departures from a station
        """
        return self.stations.get_departures(
            station_id=station_id,
            coverage=coverage,
            count=count,
            datetime=datetime
        )
        
    def check_disruptions(
        self,
        coverage: str = "sncf",
        count: int = 10,
        station_id: Optional[str] = None,
        line_id: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for current disruptions in the transport network.
        
        Args:
            coverage: The coverage area to use for the request
            count: The maximum number of disruptions to return
            station_id: Filter disruptions affecting a specific station
            line_id: Filter disruptions affecting a specific line
            since: Only disruptions valid after this date (format YYYYMMDDTHHMMSS)
            until: Only disruptions valid before this date (format YYYYMMDDTHHMMSS)
            
        Returns:
            A list of disruptions
        """
        return self.disruptions.get_disruptions(
            coverage=coverage,
            count=count,
            station_id=station_id,
            line_id=line_id,
            since=since,
            until=until
        )
        
    def get_places_nearby_station(
        self,
        station_id: str,
        coverage: str = "sncf",
        count: int = 10,
        depth: int = 2,
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
        return self.stations.get_places_nearby_station(
            station_id=station_id,
            coverage=coverage,
            count=count,
            depth=depth,
            distance=distance,
            type_list=type_list
        )
        
    def find_station_by_name(self, city: str, station_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Find a station by city and station name using pre-defined coordinates
        
        Args:
            city: The city name (e.g., "Paris", "Marseille")
            station_name: The station name (e.g., "Gare de Lyon", "Saint-Charles")
                          If None, will try to find the main station
                          
        Returns:
            Station information including ID
        """
        return self.station_finder.find_station_by_name(city, station_name) or {"error": "Station not found"}
        
    def find_station_by_coordinates(self, lat: float, lon: float, distance: int = 500) -> Dict[str, Any]:
        """
        Find a station by coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            distance: Search radius in meters
            
        Returns:
            Station information including ID
        """
        return self.station_finder.find_station_by_coordinates(lat, lon, distance) or {"error": "Station not found"}
        
    def plan_journey_with_city_names(
        self,
        from_city: str,
        to_city: str, 
        from_station: Optional[str] = None,
        to_station: Optional[str] = None,
        datetime: Optional[str] = None,
        datetime_represents: str = "departure"
    ) -> Dict[str, Any]:
        """
        Plan a journey between two cities/stations using city and station names
        
        Args:
            from_city: The departure city (e.g., "Paris")
            to_city: The arrival city (e.g., "Marseille")
            from_station: The departure station (e.g., "Gare de Lyon"), optional
            to_station: The arrival station (e.g., "Saint-Charles"), optional
            datetime: Date and time in format YYYYMMDDTHHMMSS (default: now)
            datetime_represents: Either "departure" or "arrival" (default: departure)
            
        Returns:
            Journey information or error message
        """
        return self.station_finder.find_journey_with_city_names(
            from_city=from_city,
            to_city=to_city,
            from_station=from_station,
            to_station=to_station,
            datetime=datetime,
            datetime_represents=datetime_represents
        )

    def get_vehicle_journey(
        self,
        vehicle_journey_id: str,
        coverage: str = "sncf"
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific vehicle journey (train)
        
        Args:
            vehicle_journey_id: The ID of the vehicle journey
            coverage: The coverage region
            
        Returns:
            The vehicle journey data
        """
        return self.vehicle_journey.get_vehicle_journey(
            trip_id=vehicle_journey_id,
            coverage=coverage
        )
        
    def search_train_by_number(
        self,
        train_number: str,
        date: Optional[str] = None,
        coverage: str = "sncf",
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for trains by train number
        
        Args:
            train_number: The train number to search for
            date: The date to search for (format YYYYMMDD)
            coverage: The coverage region
            count: Maximum number of results to return
            
        Returns:
            A list of vehicle journeys matching the train number
        """
        return self.vehicle_journey.search_by_train_number(
            train_number=train_number,
            date=date,
            coverage=coverage,
            count=count,
            depth=2
        )
        
    def search_train_by_line_code(
        self,
        line_code: str,
        date: Optional[str] = None,
        coverage: str = "sncf",
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for trains by line code
        
        Args:
            line_code: The line code to search for
            date: The date to search for (format YYYYMMDD)
            coverage: The coverage region
            count: Maximum number of results to return
            
        Returns:
            A list of vehicle journeys for the specified line
        """
        return self.vehicle_journey.search_by_line_code(
            line_code=line_code,
            date=date,
            coverage=coverage,
            count=count,
            depth=2
        )
    
    def search_vehicle_journeys(
        self,
        line_id: Optional[str] = None,
        route_id: Optional[str] = None,
        date: Optional[str] = None,
        coverage: str = "sncf",
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for vehicle journeys based on various criteria.
        
        Args:
            line_id: The ID of the line to search for vehicle journeys on.
            route_id: The ID of the route to search for vehicle journeys on.
            date: The date to search for vehicle journeys on (format: YYYYMMDD).
            count: The maximum number of results to return.
            coverage: The coverage area to use for the request.
            
        Returns:
            A list of dictionaries containing information about the vehicle journeys.
        """
        return self.vehicle_journey.search_vehicle_journeys(
            line_id=line_id,
            route_id=route_id,
            date=date,
            count=count,
            coverage=coverage
        )
    
    def search_train_by_number(self, train_number: str, date: Optional[str] = None, count: int = 3) -> List[Dict[str, Any]]:
        """
        Search for a train by its number.
        
        Args:
            train_number: The train number to search for
            date: The date to search for (format YYYYMMDD)
            count: The maximum number of results to return
            
        Returns:
            A list of vehicle journeys matching the train number
        """
        return self.vehicle_journey.search_by_train_number(train_number=train_number, date=date, count=count)
