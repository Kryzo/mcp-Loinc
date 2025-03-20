from typing import Dict, Any, List, Optional, Tuple, Set
import csv
import re
import os.path
import time
import json
import unicodedata
import math
import logging
from difflib import SequenceMatcher

# Configure logging with a file handler to prevent stdout interference
logger = logging.getLogger('csv_station_finder')

# Don't propagate logs to root handler (which might output to stdout)
logger.propagate = False

# Ensure handler only added once
if not logger.handlers:
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler(os.path.join('logs', 'csv_station_finder.log'))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

class CSVStationFinder:
    """
    A class that efficiently finds train stations in France using a CSV database
    """
    
    def __init__(self, csv_file_path, encoding='utf-8'):
        """
        Initialize with the CSV file path
        
        Args:
            csv_file_path: Path to the CSV file containing station data
            encoding: File encoding (default: utf-8)
        """
        self.csv_file_path = csv_file_path
        self.encoding = encoding
        self.stations_by_city = {}  # City name -> list of stations
        self.stations_by_id = {}    # Station ID -> station data
        self.cities = set()         # Set of all city names (normalized)
        self.city_name_map = {}     # Normalized city name -> original city name
        self._cached_queries = {}   # Cache for search queries
        self._last_cache_cleanup = time.time()
        self._cache_expiry = 24 * 60 * 60  # Cache expiry in seconds (24 hours)
        
        # Try different encodings if the default one fails
        encodings_to_try = [encoding, 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        for enc in encodings_to_try:
            try:
                logger.info(f"Trying encoding: {enc}")
                self.encoding = enc
                self.load_stations()
                if len(self.stations_by_id) > 0:
                    logger.info(f"Successfully loaded with encoding: {enc}")
                    break
            except Exception as e:
                logger.error(f"Failed with encoding {enc}: {str(e)}")
                
        # If we couldn't load any stations, add some hardcoded major stations
        if len(self.stations_by_id) == 0:
            logger.warning("Falling back to hardcoded stations")
            self._add_hardcoded_stations()
        
    def _normalize_text(self, text: str) -> str:
        """Normalize text for case-insensitive, accent-insensitive searching"""
        if not text:
            return ""
            
        # Convert to lowercase and strip spaces
        text = text.lower().strip()
        
        # Remove accents
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Replace special characters with spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate the similarity between two strings (0-1 where 1 is identical)"""
        return SequenceMatcher(None, str1, str2).ratio()
        
    def load_stations(self) -> None:
        """Load station data from the CSV file"""
        try:
            logger.info(f"Loading CSV file from: {self.csv_file_path}")
            
            if not os.path.exists(self.csv_file_path):
                logger.error(f"File not found: {self.csv_file_path}")
                return
                
            with open(self.csv_file_path, 'r', encoding=self.encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                
                if not reader.fieldnames:
                    logger.error("CSV file has no headers")
                    return
                    
                # Don't log the entire fieldnames collection as it might cause JSON parsing issues
                logger.info(f"CSV headers read successfully")
                
                row_count = 0
                valid_stations = 0
                
                for row in reader:
                    row_count += 1
                    
                    # Skip entries without coordinates
                    if not row.get('latitude') or not row.get('longitude'):
                        continue
                        
                    # Extract data
                    station_id = row.get('id')
                    name = row.get('name', '')
                    
                    # Handle potential parsing errors for numeric fields
                    try:
                        latitude = float(row.get('latitude', 0))
                        longitude = float(row.get('longitude', 0))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid coordinates for station ID: {station_id}")
                        continue
                        
                    country = row.get('country', '')
                    
                    # Handle boolean fields safely
                    is_city_val = row.get('is_city', '').upper()
                    is_main_val = row.get('is_main_station', '').upper()
                    
                    is_city = is_city_val == 'TRUE' if is_city_val else False
                    is_main_station = is_main_val == 'TRUE' if is_main_val else False
                    
                    parent_id = row.get('parent_station_id', '')
                    
                    # Only include French stations
                    if country != 'FR':
                        continue
                        
                    # Create station object
                    station = {
                        'id': f"stop_area:SNCF:{station_id}",  # Format to match SNCF API
                        'name': name,
                        'type': 'stop_area',
                        'coord': {'lat': latitude, 'lon': longitude},
                        'is_main_station': is_main_station,
                        'is_city': is_city,
                        'parent_id': parent_id if parent_id and parent_id != 'NA' else None
                    }
                    
                    # Store in id lookup dictionary
                    self.stations_by_id[station_id] = station
                    valid_stations += 1
                    
                    # Extract city name - either it's a city entry itself, or we extract from name
                    city_name = None
                    
                    if is_city:
                        # This entry represents a city
                        city_name = name
                    elif ' (' in name and ')' in name.split(' (')[-1]:
                        # Extract city name from parentheses in station name: "Station Name (City)"
                        city_part = name.split(' (')[-1]
                        city_name = city_part[:-1]  # Remove the closing parenthesis
                    elif ' - ' in name:
                        # Handle format "City - Station"
                        city_name = name.split(' - ')[0]
                        
                    # If we have identified a city name
                    if city_name:
                        normalized_city = self._normalize_text(city_name)
                        
                        # Store the mapping from normalized to original city name
                        if normalized_city not in self.city_name_map:
                            self.city_name_map[normalized_city] = city_name
                            
                        # Add to cities set
                        self.cities.add(normalized_city)
                        
                        # Add to city lookup dictionary
                        if normalized_city not in self.stations_by_city:
                            self.stations_by_city[normalized_city] = []
                            
                        self.stations_by_city[normalized_city].append(station)
                
                # Sort stations within each city by is_main_station flag
                for city, stations in self.stations_by_city.items():
                    self.stations_by_city[city] = sorted(
                        stations, 
                        key=lambda s: (
                            0 if s['is_main_station'] else 1,  # Main stations first
                            0 if not s['parent_id'] else 1      # Parent stations before child stations
                        )
                    )
                    
                logger.info(f"Loaded {valid_stations} stations in {len(self.cities)} cities")
                    
        except Exception as e:
            logger.error(f"Error loading station data: {str(e)}")
            # Initialize with empty data
            self.stations_by_city = {}
            self.stations_by_id = {}
            self.cities = set()
            
    def _cleanup_cache(self, force: bool = False) -> None:
        """Clean up expired cache entries"""
        current_time = time.time()
        
        # Only clean up once per hour unless forced
        if not force and (current_time - self._last_cache_cleanup < 3600):
            return
            
        expired_keys = []
        
        # Find expired cache entries
        for key, (timestamp, _) in self._cached_queries.items():
            if current_time - timestamp > self._cache_expiry:
                expired_keys.append(key)
                
        # Remove expired entries
        for key in expired_keys:
            del self._cached_queries[key]
            
        # Update last cleanup time
        self._last_cache_cleanup = current_time
            
    def find_stations_by_city(self, city: str) -> List[Dict[str, Any]]:
        """
        Find all stations in a given city
        
        Args:
            city: City name
            
        Returns:
            List of station data dictionaries
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        normalized_city = self._normalize_text(city)
        
        # Check cache
        cache_key = f"city:{normalized_city}"
        if cache_key in self._cached_queries:
            timestamp, stations = self._cached_queries[cache_key]
            if time.time() - timestamp <= self._cache_expiry:
                return stations
        
        # Exact match
        if normalized_city in self.stations_by_city:
            result = self.stations_by_city[normalized_city]
            self._cached_queries[cache_key] = (time.time(), result)
            return result
            
        # Fuzzy matching for city names
        best_match = None
        best_score = 0
        
        for city_name in self.cities:
            score = self._similarity_score(normalized_city, city_name)
            if score > best_score and score > 0.8:  # Threshold for similarity
                best_score = score
                best_match = city_name
                
        if best_match:
            result = self.stations_by_city[best_match]
            self._cached_queries[cache_key] = (time.time(), result)
            return result
            
        # No match found
        self._cached_queries[cache_key] = (time.time(), [])
        return []
        
    def find_station_by_name(self, city: str, station_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a station by city and optionally station name
        
        Args:
            city: City name
            station_name: Optional specific station name (if None, returns main station in city)
            
        Returns:
            Station data or None if not found
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        # Create cache key
        normalized_city = self._normalize_text(city)
        normalized_station = self._normalize_text(station_name) if station_name else ""
        cache_key = f"city_station:{normalized_city}:{normalized_station}"
        
        # Check cache
        if cache_key in self._cached_queries:
            timestamp, station = self._cached_queries[cache_key]
            if time.time() - timestamp <= self._cache_expiry:
                return station
        
        # Find all stations in the city
        city_stations = self.find_stations_by_city(city)
        
        if not city_stations:
            self._cached_queries[cache_key] = (time.time(), None)
            return None
            
        # If no station name provided, return the main station
        if not station_name:
            # Find the main station (should be first due to sorting in load_stations)
            for station in city_stations:
                if station['is_main_station']:
                    self._cached_queries[cache_key] = (time.time(), station)
                    return station
                    
            # If no main station found, return the first station
            self._cached_queries[cache_key] = (time.time(), city_stations[0])
            return city_stations[0]
            
        # Find station by name
        normalized_station_name = self._normalize_text(station_name)
        
        # First try exact match
        for station in city_stations:
            if self._normalize_text(station['name']) == normalized_station_name:
                self._cached_queries[cache_key] = (time.time(), station)
                return station
                
        # Then try partial match
        best_match = None
        best_score = 0
        
        for station in city_stations:
            score = self._similarity_score(normalized_station_name, self._normalize_text(station['name']))
            if score > best_score and score > 0.6:  # Threshold for similarity
                best_score = score
                best_match = station
                
        if best_match:
            self._cached_queries[cache_key] = (time.time(), best_match)
            return best_match
            
        # No match found
        self._cached_queries[cache_key] = (time.time(), None)
        return None
        
    def find_station_by_coordinates(self, lat: float, lon: float, max_distance_km: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Find the nearest station to given coordinates
        
        Args:
            lat: Latitude
            lon: Longitude
            max_distance_km: Maximum distance in kilometers (default: 2km)
            
        Returns:
            Nearest station data or None if no station within max_distance
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        # Create cache key
        cache_key = f"coord:{lat:.5f}:{lon:.5f}:{max_distance_km}"
        
        # Check cache
        if cache_key in self._cached_queries:
            timestamp, station = self._cached_queries[cache_key]
            if time.time() - timestamp <= self._cache_expiry:
                return station
                
        # Find nearest station
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station in self.stations_by_id.items():
            station_lat = station['coord']['lat']
            station_lon = station['coord']['lon']
            
            # Calculate distance using Haversine formula
            distance = self._haversine_distance(lat, lon, station_lat, station_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
                
        # Check if the nearest station is within max_distance
        if nearest_station and min_distance <= max_distance_km:
            self._cached_queries[cache_key] = (time.time(), nearest_station)
            return nearest_station
            
        # No station found within max_distance
        self._cached_queries[cache_key] = (time.time(), None)
        return None
        
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on the earth (specified in decimal degrees)
        
        Returns:
            Distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(lambda x: x * math.pi / 180, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r
        
    def search_stations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for stations by name (across all cities)
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching stations
        """
        # Clean up cache periodically
        self._cleanup_cache()
        
        # Create cache key
        normalized_query = self._normalize_text(query)
        cache_key = f"search:{normalized_query}:{limit}"
        
        # Check cache
        if cache_key in self._cached_queries:
            timestamp, stations = self._cached_queries[cache_key]
            if time.time() - timestamp <= self._cache_expiry:
                return stations
                
        # Search all stations
        matched_stations = []
        
        for station_id, station in self.stations_by_id.items():
            station_name = self._normalize_text(station['name'])
            
            # Calculate match score
            score = self._similarity_score(normalized_query, station_name)
            
            # Also check if query is a substring of station name
            if normalized_query in station_name:
                score += 0.2  # Bonus for substring match
                
            # Store if score is good enough
            if score > 0.5:  # Threshold for similarity
                matched_stations.append((score, station))
                
        # Sort by score (descending) and limit results
        results = [station for _, station in sorted(matched_stations, key=lambda x: x[0], reverse=True)[:limit]]
        
        # Cache results
        self._cached_queries[cache_key] = (time.time(), results)
        
        return results
        
    def get_all_cities(self) -> List[str]:
        """
        Get a list of all cities with train stations
        
        Returns:
            List of city names (original formatting, not normalized)
        """
        return [self.city_name_map.get(city, city) for city in self.cities]
        
    def find_journey_with_city_names(
        self,
        from_city: str,
        to_city: str,
        from_station: Optional[str] = None,
        to_station: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Find departure and arrival stations for a journey between two cities
        
        Args:
            from_city: Departure city
            to_city: Arrival city
            from_station: Optional specific departure station
            to_station: Optional specific arrival station
            
        Returns:
            Tuple of (departure_station, arrival_station), either may be None if not found
        """
        # Find departure station
        departure_station = self.find_station_by_name(from_city, from_station)
        
        # Find arrival station
        arrival_station = self.find_station_by_name(to_city, to_station)
        
        return departure_station, arrival_station
        
    def _add_hardcoded_stations(self):
        """Add hardcoded major stations as a fallback"""
        # Major stations data
        hardcoded_stations = [
            {
                "id": "87686006",
                "name": "Paris Gare de Lyon",
                "city": "Paris",
                "lat": 48.844,
                "lon": 2.373,
                "is_main": True
            },
            {
                "id": "87751008",
                "name": "Marseille Saint-Charles",
                "city": "Marseille",
                "lat": 43.303,
                "lon": 5.380,
                "is_main": True
            },
            {
                "id": "87747006",
                "name": "Grenoble",
                "city": "Grenoble",
                "lat": 45.192,
                "lon": 5.716,
                "is_main": True
            },
            {
                "id": "87722025",
                "name": "Lyon Part-Dieu",
                "city": "Lyon",
                "lat": 45.760,
                "lon": 4.860,
                "is_main": True
            },
            {
                "id": "87723197",
                "name": "Lyon Perrache",
                "city": "Lyon",
                "lat": 45.750,
                "lon": 4.826,
                "is_main": False
            },
            {
                "id": "87318964",
                "name": "Aix-en-Provence TGV",
                "city": "Aix en Provence",
                "lat": 43.455,
                "lon": 5.317,
                "is_main": True
            },
            {
                "id": "87611004",
                "name": "Versailles-Chantiers",
                "city": "Versailles",
                "lat": 48.7942,
                "lon": 2.1347,
                "is_main": True
            },
            {
                "id": "87711309",
                "name": "Versailles Rive Gauche",
                "city": "Versailles",
                "lat": 48.8031,
                "lon": 2.1271,
                "is_main": False
            },
            {
                "id": "87545210",
                "name": "Versailles Rive Droite",
                "city": "Versailles",
                "lat": 48.809,
                "lon": 2.134,
                "is_main": False
            },
            {
                "id": "87773002",
                "name": "Toulouse Matabiau",
                "city": "Toulouse",
                "lat": 43.611,
                "lon": 1.454,
                "is_main": True
            },
            {
                "id": "87756056",
                "name": "Nice Ville",
                "city": "Nice",
                "lat": 43.704,
                "lon": 7.262,
                "is_main": True
            }
        ]
        
        for station_data in hardcoded_stations:
            city = station_data["city"]
            normalized_city = self._normalize_text(city)
            
            # Create station object
            station = {
                'id': f"stop_area:SNCF:{station_data['id']}",
                'name': station_data["name"],
                'type': 'stop_area',
                'coord': {'lat': station_data["lat"], 'lon': station_data["lon"]},
                'is_main_station': station_data["is_main"],
                'is_city': False,
                'parent_id': None
            }
            
            # Add to dictionaries
            self.stations_by_id[station_data['id']] = station
            
            if normalized_city not in self.city_name_map:
                self.city_name_map[normalized_city] = city
                
            self.cities.add(normalized_city)
            
            if normalized_city not in self.stations_by_city:
                self.stations_by_city[normalized_city] = []
                
            self.stations_by_city[normalized_city].append(station)
            
        # Sort stations
        for city, stations in self.stations_by_city.items():
            self.stations_by_city[city] = sorted(
                stations, 
                key=lambda s: (0 if s['is_main_station'] else 1)
            )
            
        logger.info(f"Added {len(hardcoded_stations)} hardcoded stations")
