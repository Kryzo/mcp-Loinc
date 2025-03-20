from typing import Dict, Any, List, Optional, Tuple, Set
import requests
import json
import re
import time

# Common coordinates for major French cities and their stations
MAJOR_STATIONS = {
    "Paris": {
        "Gare de Lyon": (48.844, 2.373),
        "Gare du Nord": (48.881, 2.355),
        "Gare Montparnasse": (48.842, 2.321),
        "Gare de l'Est": (48.877, 2.359),
        "Gare Saint-Lazare": (48.876, 2.325),
        "Gare d'Austerlitz": (48.842, 2.366),
        "Gare de Bercy": (48.839, 2.382)
    },
    "Marseille": {
        "Saint-Charles": (43.303, 5.380)
    },
    "Lyon": {
        "Part-Dieu": (45.760, 4.860),
        "Perrache": (45.750, 4.826)
    },
    "Bordeaux": {
        "Saint-Jean": (44.826, -0.556)
    },
    "Lille": {
        "Flandres": (50.638, 3.072),
        "Europe": (50.639, 3.075)
    },
    "Toulouse": {
        "Matabiau": (43.611, 1.454)
    },
    "Nice": {
        "Ville": (43.704, 7.262)
    },
    "Strasbourg": {
        "Centrale": (48.585, 7.735)
    },
    "Nantes": {
        "Centrale": (47.217, -1.542)
    },
    "Rennes": {
        "Centrale": (48.103, -1.672)
    },
    "Grenoble": {
        "Gare": (45.192, 5.716)
    }
}

# Common keywords used in station names
STATION_KEYWORDS = [
    "gare", "station", "centrale", "central", "terminus", "terminal", "tgv", 
    "principale", "main", "sncf", "saint", "st-", "st "
]

class StationFinder:
    """
    Utility class to efficiently find station IDs using coordinates or names
    """
    
    def __init__(self, sncf_api):
        """
        Initialize with a SNCF API instance
        """
        self.sncf_api = sncf_api
        self._cached_coord_stations = {}  # Cache for coordinate-based lookups
        self._cached_city_stations = {}   # Cache for city-name-based lookups
        self._search_cache = {}           # Cache for search results
        self._cache_expiry = 24 * 60 * 60 # Cache expiry in seconds (24 hours)
        self._last_cache_cleanup = time.time()
        
    def _normalize_city_name(self, city: str) -> str:
        """
        Normalize city name for consistent lookups
        
        Args:
            city: City name to normalize
            
        Returns:
            Normalized city name
        """
        if not city:
            return ""
            
        # Convert to lowercase, strip whitespace
        normalized = city.lower().strip()
        
        # Remove accents - simplified approach
        accents = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c'
        }
        for acc, rep in accents.items():
            normalized = normalized.replace(acc, rep)
            
        # Remove common prefixes like "ville de", "commune de"
        prefixes = ["ville de ", "commune de ", "ville d'", "commune d'"]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
                
        return normalized
        
    def _is_main_station(self, station_name: str) -> bool:
        """
        Determine if a station is likely to be a main station based on its name
        
        Args:
            station_name: Station name to check
            
        Returns:
            True if likely a main station, False otherwise
        """
        name_lower = station_name.lower()
        
        # Check if it contains words indicating it's not a main station
        secondary_indicators = ["bis", "routiere", "annexe", "bus", "tram"]
        for indicator in secondary_indicators:
            if indicator in name_lower:
                return False
                
        # Check for main station indicators
        main_indicators = ["central", "principale", "tgv", "sncf"]
        for indicator in main_indicators:
            if indicator in name_lower:
                return True
                
        # Default to true if no negative indicators found
        return True
        
    def _rank_stations(self, stations: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
        """
        Rank stations based on relevance to the query
        
        Args:
            stations: List of station data from API
            city: City name used in query
            
        Returns:
            List of stations sorted by relevance
        """
        if not stations:
            return []
            
        # Create a scoring system
        scored_stations = []
        normalized_city = self._normalize_city_name(city)
        
        for station in stations:
            score = 0
            station_name = station.get("name", "").lower()
            station_type = station.get("type", "")
            
            # Prefer stop_area type
            if station_type == "stop_area":
                score += 100
            elif station_type == "stop_point":
                score += 50
                
            # Check if name contains city name
            if normalized_city in self._normalize_city_name(station_name):
                score += 30
                
            # Check if it contains station keywords
            for keyword in STATION_KEYWORDS:
                if keyword in station_name:
                    score += 10
                    break
                    
            # Check if it's likely a main station
            if self._is_main_station(station_name):
                score += 20
                
            # Add to scored list
            scored_stations.append((score, station))
            
        # Sort by score (descending) and return just the stations
        return [station for _, station in sorted(scored_stations, reverse=True)]
        
    def _cleanup_cache(self, force: bool = False):
        """
        Clean up expired cache entries
        
        Args:
            force: Force cleanup regardless of time since last cleanup
        """
        current_time = time.time()
        
        # Only clean up once per hour unless forced
        if not force and (current_time - self._last_cache_cleanup < 3600):
            return
            
        expired_coords = []
        expired_cities = []
        expired_searches = []
        
        # Find expired coordinate cache entries
        for key, (timestamp, _) in self._cached_coord_stations.items():
            if current_time - timestamp > self._cache_expiry:
                expired_coords.append(key)
                
        # Find expired city cache entries
        for key, (timestamp, _) in self._cached_city_stations.items():
            if current_time - timestamp > self._cache_expiry:
                expired_cities.append(key)
                
        # Find expired search cache entries
        for key, (timestamp, _) in self._search_cache.items():
            if current_time - timestamp > self._cache_expiry:
                expired_searches.append(key)
                
        # Remove expired entries
        for key in expired_coords:
            del self._cached_coord_stations[key]
            
        for key in expired_cities:
            del self._cached_city_stations[key]
            
        for key in expired_searches:
            del self._search_cache[key]
            
        # Update last cleanup time
        self._last_cache_cleanup = current_time
        
    def find_station_by_name(self, city: str, station_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a station ID by city and station name, first using pre-defined coordinates
        and then falling back to API search if needed
        
        Args:
            city: The city name (e.g., "Paris", "Marseille")
            station_name: The station name (e.g., "Gare de Lyon", "Saint-Charles")
                          If None, will try to find the main station
        
        Returns:
            Station information including ID, or None if not found
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        # Normalize city name
        city = city.strip().title()
        normalized_city = self._normalize_city_name(city)
        
        # Create cache key
        cache_key = f"{normalized_city}_{self._normalize_city_name(station_name or '')}"
        
        # Check cache
        if cache_key in self._cached_city_stations:
            timestamp, station = self._cached_city_stations[cache_key]
            # If still valid
            if time.time() - timestamp <= self._cache_expiry:
                return station
                
        # First try: Use pre-defined coordinates if available
        if city in MAJOR_STATIONS:
            # If station_name is provided, try to find it
            if station_name:
                station_name = station_name.strip()
                # Check variations of station name
                for key in MAJOR_STATIONS[city]:
                    if (self._normalize_city_name(station_name) in self._normalize_city_name(key) or 
                        self._normalize_city_name(key) in self._normalize_city_name(station_name)):
                        station = self.find_station_by_coordinates(*MAJOR_STATIONS[city][key])
                        if station:
                            # Cache the result
                            self._cached_city_stations[cache_key] = (time.time(), station)
                            return station
            
            # If no station_name provided or not found, return the first station in the city
            first_station = next(iter(MAJOR_STATIONS[city]))
            station = self.find_station_by_coordinates(*MAJOR_STATIONS[city][first_station])
            if station:
                # Cache the result
                self._cached_city_stations[cache_key] = (time.time(), station)
                return station
        
        # Second try: Search using the API
        search_query = city
        if station_name:
            search_query = f"{city} {station_name}"
            
        # Check search cache
        search_key = self._normalize_city_name(search_query)
        if search_key in self._search_cache:
            timestamp, results = self._search_cache[search_key]
            # If still valid
            if time.time() - timestamp <= self._cache_expiry:
                # Get best station from cached results
                ranked_stations = self._rank_stations(results, city)
                if ranked_stations:
                    best_station = ranked_stations[0]
                    # Cache the result
                    self._cached_city_stations[cache_key] = (time.time(), best_station)
                    return best_station
                    
        # Perform search
        places = self.sncf_api.search_places(search_query, count=10)
        
        # Cache search results
        self._search_cache[search_key] = (time.time(), places)
        
        # Rank and select the best station
        ranked_stations = self._rank_stations(places, city)
        
        if ranked_stations:
            best_station = ranked_stations[0]
            # Cache the result
            self._cached_city_stations[cache_key] = (time.time(), best_station)
            return best_station
            
        # No station found
        return None
    
    def find_station_by_coordinates(self, lat: float, lon: float, distance: int = 500) -> Optional[Dict[str, Any]]:
        """
        Find a station ID by coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            distance: Search radius in meters
            
        Returns:
            Station information including ID, or None if not found
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        # Check cache
        cache_key = f"{lat}_{lon}_{distance}"
        if cache_key in self._cached_coord_stations:
            timestamp, station = self._cached_coord_stations[cache_key]
            # If still valid
            if time.time() - timestamp <= self._cache_expiry:
                return station
            
        # Search for stations nearby
        places = self.sncf_api.search.places_nearby(
            lon=lon,
            lat=lat,
            distance=distance,
            count=5  # Get a few results in case the first one isn't ideal
        )
        
        # Find the first stop_area (station)
        for place in places:
            if place.get("type") == "stop_area":
                # Cache the result
                self._cached_coord_stations[cache_key] = (time.time(), place)
                return place
                
        # If no stop_area found, return the first place if available
        if places:
            self._cached_coord_stations[cache_key] = (time.time(), places[0])
            return places[0]
            
        return None
        
    def find_journey_with_city_names(
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
        # Find departure station
        from_place = self.find_station_by_name(from_city, from_station)
        if not from_place:
            return {"error": f"Could not find station in {from_city}"}
            
        # Find arrival station
        to_place = self.find_station_by_name(to_city, to_station)
        if not to_place:
            return {"error": f"Could not find station in {to_city}"}
            
        # Get journey
        return self.sncf_api.plan_journey(
            from_place=from_place["id"],
            to_place=to_place["id"],
            datetime=datetime,
            datetime_represents=datetime_represents
        )
        
    def get_all_stations(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """
        Get all station data currently available in the dictionary
        
        Returns:
            Copy of the MAJOR_STATIONS dictionary
        """
        return MAJOR_STATIONS.copy()
        
    def add_station(self, city: str, station_name: str, lat: float, lon: float) -> bool:
        """
        Add a new station to the MAJOR_STATIONS dictionary
        
        Args:
            city: City name
            station_name: Station name
            lat: Latitude
            lon: Longitude
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            city = city.strip().title()
            station_name = station_name.strip()
            
            # Create city entry if it doesn't exist
            if city not in MAJOR_STATIONS:
                MAJOR_STATIONS[city] = {}
                
            # Add/update station
            MAJOR_STATIONS[city][station_name] = (lat, lon)
            
            # Clear related caches
            normalized_city = self._normalize_city_name(city)
            for key in list(self._cached_city_stations.keys()):
                if key.startswith(normalized_city):
                    del self._cached_city_stations[key]
                    
            for key in list(self._search_cache.keys()):
                if normalized_city in key:
                    del self._search_cache[key]
                    
            return True
        except Exception:
            return False
            
    def export_stations_to_json(self, filepath: str) -> bool:
        """
        Export the MAJOR_STATIONS dictionary to a JSON file
        
        Args:
            filepath: Path to the output file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(MAJOR_STATIONS, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
            
    def import_stations_from_json(self, filepath: str) -> bool:
        """
        Import stations from a JSON file into MAJOR_STATIONS
        
        Args:
            filepath: Path to the input file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate and convert the data
            for city, stations in data.items():
                if not isinstance(city, str) or not isinstance(stations, dict):
                    continue
                    
                if city not in MAJOR_STATIONS:
                    MAJOR_STATIONS[city] = {}
                    
                for station_name, coords in stations.items():
                    if not isinstance(station_name, str) or not isinstance(coords, list):
                        continue
                        
                    if len(coords) != 2:
                        continue
                        
                    try:
                        lat, lon = float(coords[0]), float(coords[1])
                        MAJOR_STATIONS[city][station_name] = (lat, lon)
                    except (ValueError, TypeError):
                        continue
                        
            # Clear all caches
            self._cached_coord_stations = {}
            self._cached_city_stations = {}
            self._search_cache = {}
            
            return True
        except Exception:
            return False
