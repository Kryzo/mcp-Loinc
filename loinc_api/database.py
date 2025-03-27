"""
LOINC Database Handler
--------------------
Utilities for working with local LOINC database files.
"""

import os
import csv
import logging
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class LOINCDatabase:
    """
    Handler for local LOINC database files.
    Provides methods to load and query LOINC data from a local CSV or JSON file.
    """
    
    def __init__(self, database_path: str):
        """
        Initialize the LOINC database handler.
        
        Args:
            database_path: Path to the LOINC database file (CSV or JSON)
        """
        self.database_path = database_path
        self.data = []
        self.loaded = False
        self.file_type = os.path.splitext(database_path)[1].lower()
        
        logger.info(f"Initializing LOINC database handler with file: {database_path}")
        
    def load_database(self) -> bool:
        """
        Load the LOINC database from the file.
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.database_path):
            logger.error(f"Database file not found: {self.database_path}")
            return False
            
        try:
            if self.file_type == '.csv':
                self._load_csv()
            elif self.file_type == '.json':
                self._load_json()
            else:
                logger.error(f"Unsupported file type: {self.file_type}")
                return False
                
            self.loaded = True
            logger.info(f"Successfully loaded {len(self.data)} LOINC records")
            return True
        except Exception as e:
            logger.exception(f"Error loading database: {e}")
            return False
    
    def _load_csv(self) -> None:
        """Load LOINC data from a CSV file."""
        with open(self.database_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            self.data = list(reader)
    
    def _load_json(self) -> None:
        """Load LOINC data from a JSON file."""
        with open(self.database_path, 'r', encoding='utf-8') as file:
            self.data = json.load(file)
    
    def search(self, query: str, fields: Optional[List[str]] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for LOINC codes matching the query in specified fields.
        
        Args:
            query: Search term
            fields: List of fields to search in (if None, searches all fields)
            limit: Maximum number of results to return
            
        Returns:
            List of matching LOINC records
        """
        if not self.loaded:
            if not self.load_database():
                return []
        
        query = query.lower()
        results = []
        
        for record in self.data:
            if self._matches_query(record, query, fields):
                results.append(record)
                if len(results) >= limit:
                    break
                    
        return results
    
    def _matches_query(self, record: Dict[str, Any], query: str, fields: Optional[List[str]]) -> bool:
        """
        Check if a record matches the query in any of the specified fields.
        
        Args:
            record: LOINC record to check
            query: Search term (lowercase)
            fields: List of fields to search in (if None, searches all fields)
            
        Returns:
            True if the record matches, False otherwise
        """
        if fields:
            # Search only in specified fields
            for field in fields:
                if field in record and query in str(record[field]).lower():
                    return True
        else:
            # Search in all fields
            for value in record.values():
                if query in str(value).lower():
                    return True
                    
        return False
    
    def get_by_loinc_code(self, loinc_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a LOINC record by its code.
        
        Args:
            loinc_code: LOINC code to find
            
        Returns:
            LOINC record if found, None otherwise
        """
        if not self.loaded:
            if not self.load_database():
                return None
        
        for record in self.data:
            if record.get('LOINC_NUM') == loinc_code:
                return record
                
        return None
    
    def get_panels(self) -> List[Dict[str, Any]]:
        """
        Get all LOINC panel records.
        
        Returns:
            List of LOINC panel records
        """
        if not self.loaded:
            if not self.load_database():
                return []
        
        return [record for record in self.data if record.get('CLASS') == 'PANEL']
    
    def get_top_loinc_codes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the most common LOINC codes based on usage statistics.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of top LOINC records
        """
        if not self.loaded:
            if not self.load_database():
                return []
        
        # This is a placeholder - in a real implementation, you'd need actual usage statistics
        # For now, we'll just return the first N records
        return self.data[:limit]
