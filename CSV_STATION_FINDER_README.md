# CSV-Based SNCF Station Finder

This extension to the SNCF API wrapper provides a fast, reliable way to find train stations in France using a comprehensive CSV database instead of relying solely on API calls.

## Overview

The CSV-based station finder offers several advantages:
- **Speed**: No API calls needed for station lookups
- **Reliability**: Works even when the SNCF API is unavailable
- **Completeness**: Covers all stations in the database
- **Flexibility**: Supports fuzzy matching for city and station names

## Key Features

- **City-based station lookups**: Find stations by city name
- **Specific station lookups**: Find a specific station in a city
- **Geographic searches**: Find stations near coordinates
- **Fuzzy matching**: Find stations even with typos or alternate spellings
- **Caching**: Results are cached for improved performance
- **Comprehensive city list**: Access the full list of cities with train stations

## Usage

### Starting the Server

To start the MCP server with CSV-based station finding:

```bash
python csv_sncf_server.py --api-key YOUR_API_KEY --csv-file train_stations_europe.csv
```

### Example Usage

You can use the example script to test the functionality:

```bash
python example_csv_station_finder.py Paris "Gare de Lyon"
```

### Available Tools

The CSV-based SNCF server provides these tools:

- `find_station_by_name`: Find a station by city and station name
- `find_station_by_coordinates`: Find a station near specific coordinates
- `journey_with_city_names`: Plan a journey using city and station names
- `list_all_cities`: Get a list of all cities with train stations
- `list_stations_in_city`: Get all stations in a specific city
- `search_places`: Search for stations by name or description

## CSV File Format

The system uses a CSV file with the following columns:
- `id`: Unique station identifier
- `name`: Station name
- `latitude`, `longitude`: Geographic coordinates
- `country`: Country code (e.g., "FR" for France)
- `is_city`: Whether the entry represents a city (TRUE/FALSE)
- `is_main_station`: Whether it's a main station (TRUE/FALSE)
- `parent_station_id`: ID of the parent station (if applicable)

## How It Works

1. **Loading**: The system loads station data from the CSV file at startup
2. **Indexing**: Stations are indexed by city for fast lookups
3. **Normalization**: City and station names are normalized to remove accents, case, etc.
4. **Matching**: Fuzzy matching is used to handle variations in names
5. **Caching**: Results are cached to improve performance on repeated queries

## Integration with SNCF API

The CSV station finder is designed to integrate seamlessly with the SNCF API:
1. Find station IDs using the CSV database
2. Use those IDs with the SNCF API for journey planning
3. Get real-time data (departures, disruptions) from the SNCF API

## Advanced Features

- **Similarity scoring**: Stations are ranked by relevance to your query
- **Smart city matching**: Automatically finds the most relevant city match
- **Main station detection**: Automatically selects the main station in a city
- **Coordinate-based search**: Find stations near specific GPS coordinates

## Performance Considerations

The CSV-based approach offers excellent performance:
- Fast startup time (typically <1 second to load thousands of stations)
- Millisecond response times for station lookups
- Minimal memory footprint (typically a few MB)
- Automatic cache management to prevent memory bloat

## Example Code

```python
from sncf_api.csv_station_finder import CSVStationFinder

# Initialize the finder
finder = CSVStationFinder("train_stations_europe.csv")

# Find main station in Paris
paris_station = finder.find_station_by_name("Paris")

# Find a specific station
lyon_station = finder.find_station_by_name("Lyon", "Part-Dieu")

# Find stations for a journey
from_station, to_station = finder.find_journey_with_city_names(
    from_city="Paris",
    to_city="Marseille",
    from_station="Gare de Lyon"
)

# Find station near coordinates
nearby = finder.find_station_by_coordinates(48.844, 2.373)
```
