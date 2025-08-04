# SNOMED CT API Integration
"""
This module provides integration with SNOMED CT API for medical term validation
"""

import requests
import json
import time
from typing import List, Dict, Optional

class SnomedAPI:
    def __init__(self):
        # Using the public SNOMED CT browser API
        self.base_url = "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"
        self.edition = "MAIN"
        self.version = "MAIN"
        
        # Add simple in-memory cache and retry logic
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = 300  # 5 minutes
        self.retry_attempts = 2
        self.retry_delay = 1  # 1 second
    
    def _get_cache_key(self, term: str, operation: str = "search") -> str:
        """Generate cache key for term and operation"""
        return f"{operation}_{term.lower().strip()}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_expiry:
            return False
        return time.time() < self._cache_expiry[cache_key]
    
    def _set_cache(self, cache_key: str, value: any):
        """Set cache value with expiry"""
        self._cache[cache_key] = value
        self._cache_expiry[cache_key] = time.time() + self.cache_duration
        
        # Limit cache size to prevent memory issues
        if len(self._cache) > 1000:
            # Remove oldest entries
            current_time = time.time()
            expired_keys = [k for k, expiry in self._cache_expiry.items() if current_time >= expiry]
            for key in expired_keys[:500]:  # Remove up to 500 expired entries
                self._cache.pop(key, None)
                self._cache_expiry.pop(key, None)
    
    def _get_cache(self, cache_key: str) -> any:
        """Get cached value if valid"""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None
        
    def search_concepts(self, term: str, limit: int = 5) -> List[Dict]:
        """
        Search for SNOMED CT concepts matching the given term with caching and retry
        
        Args:
            term: The search term
            limit: Maximum number of results to return
            
        Returns:
            List of concept dictionaries
        """
        # Check cache first
        cache_key = self._get_cache_key(term, f"search_{limit}")
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Try API call with retry logic
        for attempt in range(self.retry_attempts + 1):
            try:
                url = f"{self.base_url}/browser/{self.edition}/concepts"
                params = {
                    "term": term,
                    "activeFilter": True,
                    "termActive": True,
                    "limit": limit,
                    "offset": 0,
                    "groupByConcept": True,
                    "searchMode": "partialMatching",
                    "lang": "english",
                    "skipTo": 0,
                    "returnLimit": limit
                }
                
                # Reduced timeout to 3 seconds
                response = requests.get(url, params=params, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("items", [])
                    # Cache successful result
                    self._set_cache(cache_key, result)
                    return result
                elif response.status_code == 429:
                    print(f"SNOMED API rate limited for term '{term}' (attempt {attempt + 1})")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    # Cache empty result for rate limits
                    self._set_cache(cache_key, [])
                    return []
                else:
                    print(f"SNOMED API error: {response.status_code} for term '{term}'")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                        continue
                    return []
                    
            except requests.exceptions.Timeout:
                print(f"SNOMED API timeout for term '{term}' (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                return []
            except requests.exceptions.RequestException as e:
                print(f"SNOMED API request error: {e} (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                return []
            except Exception as e:
                print(f"SNOMED API error: {e}")
                return []
        
        return []
    
    def validate_term(self, term: str) -> bool:
        """
        Validate if a term exists in SNOMED CT with caching
        
        Args:
            term: The term to validate
            
        Returns:
            True if the term is valid, False otherwise
        """
        # Check cache first
        cache_key = self._get_cache_key(term, "validate")
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            results = self.search_concepts(term, limit=1)
            is_valid = len(results) > 0
            # Cache the validation result
            self._set_cache(cache_key, is_valid)
            return is_valid
        except Exception as e:
            print(f"SNOMED validation error for term '{term}': {e}")
            # Cache negative result for failed validations
            self._set_cache(cache_key, False)
            return False
    
    def get_suggestions(self, term: str, max_suggestions: int = 3) -> List[str]:
        """
        Get spelling suggestions from SNOMED CT
        
        Args:
            term: The term to get suggestions for
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested terms
        """
        try:
            concepts = self.search_concepts(term, limit=max_suggestions)
            suggestions = []
            
            for concept in concepts:
                # Get the preferred term
                pt = concept.get("pt", {})
                if pt and pt.get("term"):
                    suggestions.append(pt["term"])
                
                # Also check for fully specified name
                fsn = concept.get("fsn", {})
                if fsn and fsn.get("term"):
                    # Extract just the term part (before the semantic tag)
                    fsn_term = fsn["term"].split("(")[0].strip()
                    if fsn_term not in suggestions:
                        suggestions.append(fsn_term)
            
            return suggestions[:max_suggestions]
        except Exception as e:
            print(f"SNOMED suggestions error for term '{term}': {e}")
            return []
    
    def get_concept_details(self, concept_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific concept
        
        Args:
            concept_id: The SNOMED CT concept ID
            
        Returns:
            Concept details dictionary or None
        """
        try:
            url = f"{self.base_url}/{self.version}/concepts/{concept_id}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Error getting concept details: {e}")
            return None
    
    def find_medication(self, medication_name: str) -> List[Dict]:
        """
        Find medication concepts in SNOMED CT
        
        Args:
            medication_name: Name of the medication
            
        Returns:
            List of medication concepts
        """
        try:
            # Search with semantic tag for pharmaceutical products
            results = self.search_concepts(medication_name, limit=5)
            
            # Filter for medication-related concepts
            medications = []
            for concept in results:
                fsn = concept.get("fsn", {}).get("term", "")
                # Check if it's a pharmaceutical/medicinal product
                if any(tag in fsn.lower() for tag in ["(medicinal product)", "(product)", "(substance)"]):
                    medications.append(concept)
            
            return medications
        except Exception as e:
            print(f"Error finding medication '{medication_name}': {e}")
            return []
