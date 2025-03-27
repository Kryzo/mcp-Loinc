"""
LOINC API Configuration
---------------------
Configuration constants for the LOINC API.
"""

# Default values for API queries
DEFAULT_LIMIT = 20
DEFAULT_DATA_VERSION = "current"
DEFAULT_FORMAT = "json"

# Base URL for the LOINC API
BASE_URL = "https://loinc.regenstrief.org/searchapi/"

# LOINC API endpoints
ENDPOINTS = {
    "loincs": "loincs",
    "answerlists": "answerlists",
    "parts": "parts",
    "groups": "groups",
    "multiaxial": "multiaxial",
    "forms": "forms",
    "panels": "panels",
    "top2000": "top2000"
}
