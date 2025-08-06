# SNOMED CT API Integration
"""
This module provides integration with SNOMED CT API for medical term validation
"""

import requests
import json
import time
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .database_cache import get_database_cache
from .performance_monitor import get_performance_monitor

class SnomedAPI:
    def __init__(self):
        # Using the authenticated SNOMED API from haiapi.shaip.com
        self.base_url = "https://haiapi.shaip.com/snomed_output"
        
        # Read API key from environment variable first, then fallback to hardcoded
        self.api_key = os.getenv("X_API_KEY")
        if not self.api_key:
            print("⚠️  X_API_KEY not found in environment, using hardcoded fallback")
            self.api_key = "027554fd-92c9-48ff-9302-ff6efae8eb4f"  # Updated to new valid key
        else:
            print(f"✅ SNOMED API key loaded from environment: {self.api_key[:8]}...")
        
        # Verify API key is valid (should be UUID format)
        if len(self.api_key) == 36 and self.api_key.count('-') == 4:
            print(f"✅ API key format appears valid: {self.api_key[:8]}...{self.api_key[-4:]}")
        else:
            print(f"⚠️  API key format may be invalid: {len(self.api_key)} chars")
        
        # Legacy fields for backward compatibility (not used with new API)
        self.edition = "MAIN"
        self.version = "MAIN"
        
        # Add simple in-memory cache and retry logic
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = 300  # 5 minutes
        self.retry_attempts = 1  # Reduced from 2 to 1 retry (total 2 attempts)
        self.retry_delay = 1  # 1 second
        
        # Circuit breaker pattern to prevent cascading failures
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 2  # Open circuit after 2 consecutive failures
        self.circuit_breaker_timeout = 60  # Keep circuit open for 60 seconds
        self.circuit_breaker_opened_at = None
        self.circuit_breaker_state = "closed"  # closed, open, half-open
        
        # Initialize database cache
        self.db_cache = get_database_cache()

        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()
    
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
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.circuit_breaker_state == "closed":
            return False
        elif self.circuit_breaker_state == "open":
            # Check if timeout has expired
            if self.circuit_breaker_opened_at and \
               datetime.now() > self.circuit_breaker_opened_at + timedelta(seconds=self.circuit_breaker_timeout):
                self.circuit_breaker_state = "half-open"
                print("SNOMED API circuit breaker moving to half-open state")
                return False
            return True
        else:  # half-open
            return False
    
    def _record_success(self):
        """Record successful API call"""
        if self.circuit_breaker_state == "half-open":
            print("SNOMED API circuit breaker closing after successful call")
            self.circuit_breaker_state = "closed"
        self.circuit_breaker_failures = 0
    
    def _record_failure(self):
        """Record failed API call"""
        self.circuit_breaker_failures += 1
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_state = "open"
            self.circuit_breaker_opened_at = datetime.now()
            print(f"SNOMED API circuit breaker opened after {self.circuit_breaker_failures} failures")
    
    def _should_skip_api_call(self) -> bool:
        """Check if API call should be skipped due to circuit breaker"""
        if self._is_circuit_open():
            print("SNOMED API circuit breaker is open, skipping API call")
            return True
        return False
    
    def _parse_haiapi_response(self, response_data: Dict, limit: int = 5) -> List[Dict]:
        """
        Parse the response from haiapi.shaip.com SNOMED API
        
        Args:
            response_data: Raw response from the API
            limit: Maximum number of results to return
            
        Returns:
            List of standardized concept dictionaries
        """
        try:
            results = []
            
            # The API response format may vary, so we need to handle different structures
            if isinstance(response_data, dict):
                # Look for SNOMED codes or medical terms in the response
                if 'concepts' in response_data:
                    concepts = response_data['concepts']
                elif 'results' in response_data:
                    concepts = response_data['results']
                elif 'data' in response_data:
                    concepts = response_data['data']
                else:
                    # If the response contains SNOMED codes directly
                    concepts = [response_data] if response_data else []
                
                # Convert to standardized format
                for i, concept in enumerate(concepts[:limit]):
                    if isinstance(concept, dict):
                        # Standardize the concept format
                        standardized = {
                            "conceptId": concept.get("conceptId", concept.get("id", f"unknown_{i}")),
                            "pt": {
                                "term": concept.get("preferredTerm", concept.get("term", concept.get("display", "")))
                            },
                            "fsn": {
                                "term": concept.get("fullySpecifiedName", concept.get("fsn", ""))
                            }
                        }
                        results.append(standardized)
                    elif isinstance(concept, str):
                        # If concept is just a string (term)
                        results.append({
                            "conceptId": f"term_{i}",
                            "pt": {"term": concept},
                            "fsn": {"term": concept}
                        })
            
            return results[:limit]
            
        except Exception as e:
            print(f"Error parsing haiapi response: {e}")
            return []
        
    def search_concepts(self, term: str, limit: int = 5) -> List[Dict]:
        """
        Search for SNOMED CT concepts using the authenticated haiapi.shaip.com API
        
        Args:
            term: The search term
            limit: Maximum number of results to return
            
        Returns:
            List of concept dictionaries
        """
        # Check database cache first
        if self.db_cache and self.db_cache.is_available:
            cached_result = self.db_cache.get_snomed_cache(term)
            if cached_result:
                print(f"✅ SNOMED database cache hit for: {term}")
                self.performance_monitor.log_cache_hit('snomed', 'search')
                self.db_cache.log_usage_stats(
                    endpoint='snomed', operation='search', cache_hit=True,
                    processing_time_ms=0
                )
                # Parse cached response
                try:
                    api_response = cached_result['api_response']
                    if isinstance(api_response, str):
                        api_response = json.loads(api_response)
                    return self._parse_haiapi_response(api_response, limit)
                except Exception as e:
                    print(f"Error parsing cached SNOMED response: {e}")
                    # Fall through to API call
        
        # Check in-memory cache as fallback
        cache_key = self._get_cache_key(term, f"search_{limit}")
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            self.performance_monitor.log_cache_hit('snomed', 'search')
            return cached_result
        
        # Check circuit breaker before making API calls
        if self._should_skip_api_call():
            # Return empty result when circuit is open
            self._set_cache(cache_key, [])
            return []
        
        self.performance_monitor.log_cache_miss('snomed', 'search')
        # Try API call with retry logic
        start_time = time.time()
        for attempt in range(self.retry_attempts + 1):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key
                }
                
                payload = {
                    "data": term
                }
                
                # Increased timeout to 8 seconds for better reliability
                response = requests.post(self.base_url, json=payload, headers=headers, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    self.performance_monitor.log_response_time('snomed', 'search', processing_time_ms)
                    
                    # Parse the response from the new API format
                    result = self._parse_haiapi_response(data, limit)
                    
                    # Cache successful result in memory
                    self._set_cache(cache_key, result)
                    
                    # Cache in database for persistence
                    if self.db_cache and self.db_cache.is_available:
                        try:
                            self.db_cache.set_snomed_cache(
                                search_term=term,
                                api_response=data,
                                concept_count=len(result),
                                is_valid=True,
                                response_time_ms=processing_time_ms
                            )
                            self.db_cache.log_usage_stats(
                                endpoint='snomed', operation='search', cache_hit=False,
                                processing_time_ms=processing_time_ms,
                                response_size_bytes=len(json.dumps(data))
                            )
                        except Exception as cache_error:
                            print(f"Error caching SNOMED response: {cache_error}")
                    
                    # Record success for circuit breaker
                    self._record_success()
                    return result
                elif response.status_code == 500:
                    print(f"SNOMED API server error for term '{term}' (attempt {attempt + 1})")
                    self._record_failure() # Record failure for 500 errors
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return []
                else:
                    print(f"SNOMED API error: {response.status_code} for term '{term}' - {response.text}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                        continue
                    return []
                    
            except requests.exceptions.Timeout:
                print(f"SNOMED API timeout for term '{term}' (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                # Record failure on final attempt
                self._record_failure()
                return []
            except requests.exceptions.RequestException as e:
                print(f"SNOMED API request error: {e} (attempt {attempt + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                # Record failure on final attempt
                self._record_failure()
                return []
            except Exception as e:
                print(f"SNOMED API error: {e}")
                self._record_failure()
                return []
        
        # Record failure if all attempts exhausted
        self._record_failure()
        
        # Log failed API call
        processing_time_ms = int((time.time() - start_time) * 1000)
        if self.db_cache and self.db_cache.is_available:
            self.db_cache.log_usage_stats(
                endpoint='snomed', operation='search', cache_hit=False,
                processing_time_ms=processing_time_ms, error_occurred=True,
                error_message="All API attempts failed"
            )
        
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
            response = requests.get(url, timeout=8)
            
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
