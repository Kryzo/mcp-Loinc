# SNCF API MCP Server

This project provides a modular Python wrapper for the SNCF API, with an MCP server interface that integrates seamlessly with Claude Desktop for intelligent journey planning and train information retrieval across France.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Getting an API Key](#getting-an-api-key)
- [Configuration](#configuration)
  - [Setting Up Claude Desktop](#setting-up-claude-desktop)
  - [Environment Variables](#environment-variables)
- [Available MCP Tools](#available-mcp-tools)
  - [Journey Planning](#journey-planning)
  - [Station Information](#station-information)
  - [Disruption Monitoring](#disruption-monitoring)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Features](#advanced-features)

## Overview

The SNCF MCP Server provides a comprehensive interface to the French National Railway's (SNCF) API services, allowing you to:

- Plan train journeys between cities in France
- Get detailed information about train stations
- Check schedules for departures and arrivals
- Monitor service disruptions
- Find nearby places and transport options

The structure is organized as follows:

- `sncf_api/` - The main package for SNCF API interaction
  - `__init__.py` - Package initialization
  - `config.py` - Configuration settings
  - `client.py` - Base API client
  - `api.py` - Main API interface combining all modules
  - `search.py` - Search-related endpoints
  - `journey.py` - Journey planning endpoints
  - `stations.py` - Station-related endpoints
  - `networks.py` - Network and transport mode endpoints
  - `disruptions.py` - Disruption-related endpoints
  - `station_finder.py` - Efficient station lookup by coordinates
  - `csv_station_finder.py` - Station lookup using CSV database
  - `vehicle_journey.py` - Detailed train journey information
- `sncf_server.py` - MCP server implementation with all tool endpoints
- `train_stations_europe.csv` - Database of European train stations with coordinates

## Features

- **Intelligent Journey Planning**: Plan trips between any cities in France with automatic station selection
- **Comprehensive Station Details**: Get detailed information about stations including:
  - Available transport types (trains, buses, trams)
  - Nearby places and points of interest
  - Coordinates and accessibility information
- **Real-time Schedules**: Access up-to-date departure and arrival information
- **Disruption Monitoring**: Stay informed about service disruptions
- **Smart Station Finding**: Locate stations by city name, station name, or coordinates
- **Fallback Mechanisms**: Hardcoded coordinates for major cities ensure reliability even when API searches fail
- **Detailed Logging**: Comprehensive logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.6+
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/sncf-mcp-new.git
cd sncf-mcp-new
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

If the requirements.txt file is missing, install the following packages:
requests
mcp

```bash
pip install requests pandas mcp
```

## Getting an API Key

Before using this server, you need to obtain an API key from SNCF:

1. Visit the [SNCF API Portal](https://www.digital.sncf.com/startup/api)
2. Create an account or log in
3. Subscribe to the "Navitia" API service
4. Complete the registration process
5. Once approved, you'll receive your API key in your account dashboard

The API key looks like a UUID string (e.g., `01293485-3NS3-3242-23AZ-3241324512`).

## Configuration

### Setting Up Claude Desktop

To integrate the SNCF MCP tools with Claude Desktop:

1. **Install Claude Desktop** if you haven't already
2. **Open Claude Desktop Configuration**:
   - Navigate to the Claude Desktop settings
   - Open the configuration file (usually located at `%APPDATA%\Claude\claude_desktop_config.json`)

```json
{
 "sncf": {
  "command": "py",
  "args": [
    "c:\\Users\\ChristianELHAJJ\\sncf-mcp-new\\sncf_server.py",
    "--api-key={YOUR-API-KEY}"
  ],
  "cwd": "c:\\Users\\ChristianELHAJJ\\sncf-mcp-new"
},
```

Replace `path/to/sncf-mcp-new` with the actual path to your installation directory.

3. **Save the Configuration File** and restart Claude Desktop

## Available MCP Tools

Once configured, the following tools will be available to Claude Desktop:

### Journey Planning

#### `plan_journey_by_city_names`

Plan a journey between two cities in France.

**Parameters:**
- `from_city`: Departure city name (e.g., "Paris")
- `to_city`: Destination city name (e.g., "Marseille")
- `datetime`: Optional departure or arrival time (format: YYYYMMDDTHHMMSS)
- `datetime_represents`: "departure" or "arrival" (default: "departure")
- `include_station_details`: Whether to include detailed station information

**Example prompt for Claude:**
```
Plan a train journey from Paris to Lyon tomorrow morning at 8 AM.
```

### Station Information

#### `get_station_details`

Get comprehensive details about train stations in a city.

**Parameters:**
- `city_name`: Name of the city to search for stations
- `station_name`: Optional specific station name
- `station_id`: Optional direct station ID
- `include_transport_types`: Whether to include transport type analysis
- `include_nearby_places`: Whether to include nearby places information
- `nearby_distance`: Search radius in meters for nearby places
- `nearby_count`: Maximum number of nearby places to return

**Example prompt for Claude:**
```
What transport options are available at the main train station in Grenoble?
```

#### `get_station_schedule`

Get departure and arrival schedules for a station.

**Parameters:**
- `city_name`: Name of the city to search for stations
- `station_name`: Optional specific station name
- `station_id`: Optional direct station ID
- `count`: Number of departures/arrivals to return
- `datetime`: Optional datetime to start from
- `duration`: Optional duration in seconds
- `data_freshness`: Data freshness level (realtime or base_schedule)

**Example prompt for Claude:**
```
Show me the next 5 train departures from Paris Gare de Lyon.
```

### Disruption Monitoring

#### `check_disruptions`

Check for current disruptions in the SNCF transport network.

**Parameters:**
- `coverage`: The coverage area (default: "sncf")
- `count`: Maximum number of disruptions to return
- `station_id`: Optional filter for a specific station
- `line_id`: Optional filter for a specific line
- `since`: Only disruptions valid after this date
- `until`: Only disruptions valid before this date
- `fetch_train_details`: Whether to fetch additional details about affected trains

**Example prompt for Claude:**
```
Are there any current disruptions affecting trains to Marseille?
```

## Usage Examples

### Planning a Journey

You can ask Claude to plan a journey between any two cities in France:

```
I need to travel from Paris to Nice next Friday at 2 PM. Can you find me a train?
```

Claude will use the `plan_journey_by_city_names` tool to:
1. Find the main stations in both cities
2. Plan the optimal journey between them
3. Present you with departure/arrival times, durations, and connection details

### Getting Station Information

To get detailed information about a station:

```
What facilities and transport options are available at Gare de Lyon in Paris?
```

Claude will use the `get_station_details` tool to provide:
1. Basic station information (name, ID, coordinates)
2. Available transport types (trains, buses, trams)
3. Nearby places and points of interest

### Checking Train Schedules

To check upcoming departures or arrivals:

```
When are the next trains leaving from Bordeaux to Paris today?
```

Claude will use the `get_station_schedule` tool to show:
1. Upcoming departures from Bordeaux
2. Destination information
3. Platform details when available
4. Real-time status updates

### Monitoring Disruptions

To check for service disruptions:

```
Are there any disruptions affecting the Paris to Lyon route today?
```

Claude will use the `check_disruptions` tool to:
1. Find relevant disruptions
2. Explain the impact on services
3. Provide additional details about affected trains

## Troubleshooting

### Common Issues

#### "No API key provided"
- Ensure you've added your SNCF API key to the Claude Desktop configuration
- Check that the environment variable is correctly referenced in the MCP server configuration

#### "No stations found for city"
- Try using a more specific city name
- For smaller cities, try using the name of a nearby larger city
- The system has hardcoded coordinates for major French cities which should work reliably

#### "Failed to connect to SNCF API"
- Check your internet connection
- Verify that your API key is valid and not expired
- The SNCF API may be experiencing downtime; try again later

#### "Error initializing CSV station finder"
- Ensure the train_stations_europe.csv file is in the correct location
- Check file permissions to ensure the file is readable

## Advanced Features

### Hardcoded Coordinates

The system includes hardcoded coordinates for major French cities to ensure reliability even when the API search fails:

- Paris (48.853, 2.348)
- Marseille (43.303, 5.380)
- Lyon (45.760, 4.860)
- Toulouse (43.611, 1.454)
- Nice (43.704, 7.262)
- Nantes (47.217, -1.542)
- Strasbourg (48.585, 7.735)
- Bordeaux (44.826, -0.556)
- Lille (50.638, 3.072)
- Rennes (48.103, -1.672)
- Grenoble (45.192, 5.716)

### Transport Type Analysis

The `get_station_details` tool can analyze and categorize the types of transport available at a station:

- Long-distance trains (TGV, Intercités)
- Regional trains (TER)
- Local transit (buses, trams, metros)
- Other services (taxis, bike sharing)

### Nearby Places Search

The station details tool can find points of interest near a station:

- Other transport stops
- Public facilities
- Points of interest
- Address points

This feature is particularly useful for travelers planning their onward journey from a station.

---

## Contributing

Contributions to improve the SNCF MCP Server are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SNCF for providing the API
- The Navitia team for their comprehensive public transport API
- Claude AI for intelligent integration capabilities


created by Christian delage (dr.christian.delage@gmail.com)
