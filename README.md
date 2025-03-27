# LOINC API MCP Server

This project provides a modular Python wrapper for the LOINC API, with an MCP server interface that integrates seamlessly with Claude Desktop for intelligent medical terminology lookup and standardization.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Getting LOINC API Access](#getting-loinc-api-access)
- [Configuration](#configuration)
  - [Setting Up Claude Desktop](#setting-up-claude-desktop)
  - [Authentication](#authentication)
- [Available MCP Tools](#available-mcp-tools)
  - [LOINC Code Search](#loinc-code-search)
  - [LOINC Details Retrieval](#loinc-details-retrieval)
  - [Panel Information](#panel-information)
  - [Hierarchy Navigation](#hierarchy-navigation)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Features](#advanced-features)

## Overview

The LOINC MCP Server provides a comprehensive interface to the Logical Observation Identifiers Names and Codes (LOINC) API services, allowing you to:

- Search for LOINC codes by various terms and filters
- Retrieve detailed information about specific LOINC codes
- Access standardized panels and forms
- Navigate hierarchical relationships between LOINC terms
- Retrieve answer lists for LOINC observations

The structure is organized as follows:

- `loinc_api/` - The main package for LOINC API interaction
  - `__init__.py` - Package initialization
  - `config.py` - Configuration settings
  - `api.py` - Main API client with HTTP Basic Authentication
  - `database.py` - Local database handler for offline access

## Features

- **Comprehensive LOINC Search**: Find LOINC codes using free text queries with filtering options for component, property, system, and class
- **Detailed LOINC Information**: Access complete details for any LOINC code including formal name, component, property, system, method, and more
- **Panel Structure Access**: Explore LOINC panels and their component tests
- **Hierarchical Navigation**: Navigate parent-child relationships between LOINC terms
- **Standardized Forms**: Access LOINC's standardized assessment forms and questionnaires
- **Top 2000 Access**: Retrieve the most commonly used LOINC codes
- **Answer Lists**: Get standardized answer lists for specific LOINC observations
- **Dual Mode Operation**: Work with either the online LOINC API or a local database file
- **MCP Integration**: Seamless integration with Claude Desktop via the MCP protocol

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/loinc-api.git
   cd loinc-api
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Getting LOINC API Access

To use the LOINC API, you need to:

1. Register for a free account at [LOINC.org](https://loinc.org/register/)
2. Accept the terms of use
3. Once registered, you can use your LOINC.org username and password for API authentication

## Configuration

### Setting Up Claude Desktop

To integrate with Claude Desktop, add the following configuration to your Claude Desktop config file:

```json
{
  "mcp_servers": [
    {
      "name": "LOINC API",
      "url": "http://localhost:8080",
      "auth": {
        "type": "basic",
        "username": "your_loinc_username",
        "password": "your_loinc_password"
      }
    }
  ]
}
```

### Authentication

The LOINC API uses HTTP Basic Authentication. You'll need to provide your LOINC username and password when starting the server:

```bash
python loinc_server.py --username=your_loinc_username --password=your_loinc_password
```

## Available MCP Tools

### LOINC Code Search

Search for LOINC codes with various filters:

```json
{
  "query": "glucose",
  "limit": 10,
  "component_filter": "Glucose",
  "system_filter": "Blood",
  "include_details": true
}
```

### LOINC Details Retrieval

Get comprehensive information about a specific LOINC code:

```json
{
  "loinc_code": "2339-0"
}
```

### Panel Information

Retrieve the structure of LOINC panels:

```json
{
  "loinc_code": "24331-1"
}
```

### Hierarchy Navigation

Explore parent-child relationships:

```json
{
  "parent": "LP7839-6"
}
```

## Usage Examples

**Example 1: Search for glucose-related LOINC codes**

```json
{
  "query": "glucose",
  "limit": 5,
  "include_details": true
}
```

**Example 2: Get detailed information about a specific LOINC code**

```json
{
  "loinc_code": "2339-0"
}
```

## Troubleshooting

- **Empty Results**: Ensure your LOINC account has the proper permissions and that you're using the correct authentication credentials
- **Connection Issues**: Check your internet connection and verify the LOINC API is accessible
- **Authentication Errors**: Confirm your LOINC username and password are correct

## Advanced Features

- **Local Database**: For offline use, you can create a local LOINC database file:
  ```bash
  python loinc_server.py --create-db --username=your_loinc_username --password=your_loinc_password
  ```

- **Custom Filtering**: Apply advanced filters to narrow down search results:
  ```json
  {
    "query": "hemoglobin",
    "property_filter": "Mass",
    "system_filter": "Blood",
    "class_filter": "CHEM"
  }
  ```

## Contributing

Contributions to improve the LOINC MCP Server are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is opensourced
## Acknowledgments

- LOINC for providing the API
- The LOINC team for their comprehensive medical terminology standardization
- Claude AI for intelligent integration capabilities

created by Christian delage (dr.christian.delage@gmail.com)
