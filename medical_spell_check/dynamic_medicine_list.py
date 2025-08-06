# Dynamic Medicine List
"""
This module provides a dynamic, self-growing medicine list that learns from user interactions
and serves as a primary filter before calling SNOMED CT API.
Now enhanced with database storage for better performance and persistence.
"""

import json
import os
from typing import Set, List, Dict, Optional
from datetime import datetime
from .database_cache import get_database_cache

class DynamicMedicineList:
    def __init__(self, storage_file: str = "dynamic_medicine_list.json"):
        self.storage_file = storage_file
        self.medicine_list: Set[str] = set()
        self.cache: Dict[str, Dict] = {}  # Legacy SNOMED cache (fallback)
        self.classification_cache: Dict[str, bool] = {}  # Legacy LLM classification cache (fallback)
        
        # Initialize database cache
        self.db_cache = get_database_cache()
        self._use_database = self.db_cache and self.db_cache.is_available
        
        if self._use_database:
            print("✅ Dynamic medicine list using database storage")
            self.load_from_database()
        else:
            print("⚠️  Database unavailable, falling back to JSON file storage")
            self.load_medicine_list()
        
        # Simple common words to skip (very basic list)
        self.skip_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'his', 'hers', 'ours', 'theirs'
        }
    
    def _validate_json_file(self, file_path: str) -> bool:
        """
        Validate that a JSON file can be loaded without errors
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            print(f"JSON validation failed for {file_path}: {e}")
            return False
    
    def _create_backup(self, file_path: str):
        """Create a backup of the current file"""
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
            except Exception as e:
                print(f"Failed to create backup: {e}")

    def load_from_database(self):
        """Load medicine list from database"""
        try:
            if not self.db_cache or not self.db_cache.is_available:
                return
            
            # Get all medicines from database
            cursor = self.db_cache._get_cursor()
            if not cursor:
                return
            
            try:
                query = "SELECT medicine_name FROM medicine_list_extended WHERE confirmed_correct = true"
                cursor.execute(query)
                results = cursor.fetchall()
                
                self.medicine_list = {row['medicine_name'].lower() for row in results}
                print(f"Loaded {len(self.medicine_list)} medicines from database")
                
                cursor.close()
            except Exception as e:
                print(f"Error querying database for medicines: {e}")
                if cursor:
                    cursor.close()
                    
        except Exception as e:
            print(f"Error loading medicines from database: {e}")
            # Fallback to JSON loading
            self.load_medicine_list()

    def load_medicine_list(self):
        """Load the dynamic medicine list from disk with validation"""
        try:
            if os.path.exists(self.storage_file):
                # Validate JSON before loading
                if not self._validate_json_file(self.storage_file):
                    print(f"Corrupted JSON detected in {self.storage_file}")
                    # Create backup of corrupted file
                    self._create_backup(self.storage_file)
                    # Delete corrupted file and start fresh
                    os.remove(self.storage_file)
                    print(f"Removed corrupted file: {self.storage_file}")
                    # Initialize with empty data
                    self.medicine_list = set()
                    self.cache = {}
                    self.classification_cache = {}
                    return
                
                # Load validated JSON
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.medicine_list = set(data.get('medicines', []))
                    self.cache = data.get('cache', {})
                    self.classification_cache = data.get('classification_cache', {})
                print(f"Loaded {len(self.medicine_list)} medicines from dynamic list")
            else:
                # File doesn't exist, start fresh
                self.medicine_list = set()
                self.cache = {}
                self.classification_cache = {}
                print("Starting with empty dynamic medicine list")
        except Exception as e:
            print(f"Error loading dynamic medicine list: {e}")
            # Fallback to empty data
            self.medicine_list = set()
            self.cache = {}
            self.classification_cache = {}
            # Try to create backup if file exists
            if os.path.exists(self.storage_file):
                self._create_backup(self.storage_file)
    
    def _sanitize_data_for_json(self, data):
        """
        Recursively sanitize data to ensure JSON serialization compatibility
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data safe for JSON serialization
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                try:
                    # Try to serialize the key-value pair
                    json.dumps({key: value})
                    sanitized[key] = self._sanitize_data_for_json(value)
                except (TypeError, ValueError) as e:
                    print(f"Skipping non-serializable data for key '{key}': {e}")
                    # Skip non-serializable data
                    continue
            return sanitized
        elif isinstance(data, list):
            sanitized = []
            for item in data:
                try:
                    # Try to serialize the item
                    json.dumps(item)
                    sanitized.append(self._sanitize_data_for_json(item))
                except (TypeError, ValueError):
                    # Skip non-serializable items
                    continue
            return sanitized
        elif isinstance(data, (str, int, float, bool)) or data is None:
            return data
        else:
            # For other types, try to convert to string or skip
            try:
                json.dumps(data)
                return data
            except (TypeError, ValueError):
                print(f"Skipping non-serializable data of type {type(data)}")
                return None

    def save_medicine_list(self):
        """Save the dynamic medicine list to disk with robust error handling"""
        try:
            data = {
                'medicines': list(self.medicine_list),
                'cache': self.cache,
                'classification_cache': self.classification_cache,
                'last_updated': datetime.now().isoformat()
            }
            
            # Sanitize data before saving
            sanitized_data = self._sanitize_data_for_json(data)
            
            # Test serialization before writing to file
            json.dumps(sanitized_data)
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
                
        except (TypeError, ValueError) as e:
            print(f"JSON serialization error saving dynamic medicine list: {e}")
            # Try to save without cache data if main serialization fails
            try:
                fallback_data = {
                    'medicines': list(self.medicine_list),
                    'cache': {},  # Empty cache to avoid serialization issues
                    'classification_cache': {},  # Empty cache
                    'last_updated': datetime.now().isoformat(),
                    'error_note': 'Cache data was cleared due to serialization issues'
                }
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(fallback_data, f, indent=2, ensure_ascii=False)
                print("Saved dynamic medicine list with cleared cache data as fallback")
            except Exception as fallback_error:
                print(f"Fallback save also failed: {fallback_error}")
        except Exception as e:
            print(f"Error saving dynamic medicine list: {e}")
            # Log the problematic data for debugging
            print(f"Data types in cache: {[type(v) for v in self.cache.values()]}")
            print(f"Data types in classification_cache: {[type(v) for v in self.classification_cache.values()]}")
    
    def add_medicine(self, term: str, category: str = 'medication', 
                    confirmed_correct: bool = True, user_confirmed: bool = True,
                    snomed_code: str = None, generic_name: str = None,
                    brand_names: List[str] = None, common_misspellings: List[str] = None):
        """Add a medicine term to the dynamic list and database"""
        if not term or not term.strip():
            return
            
        clean_term = term.strip().lower()
        if clean_term in self.medicine_list or clean_term in self.skip_words:
            return
            
        # Add to in-memory set for current session
        self.medicine_list.add(clean_term)
        
        # Save to database if available
        if self._use_database:
            success = self.db_cache.add_medicine_to_extended_list(
                medicine_name=clean_term,
                category=category,
                confirmed_correct=confirmed_correct,
                user_confirmed=user_confirmed,
                snomed_code=snomed_code,
                generic_name=generic_name,
                brand_names=brand_names,
                common_misspellings=common_misspellings
            )
            if success:
                print(f"✅ Added medicine to database: {clean_term}")
            else:
                print(f"⚠️  Failed to add medicine to database, falling back to JSON: {clean_term}")
                self.save_medicine_list()
        else:
            # Fallback to JSON storage
            self.save_medicine_list()
            print(f"Added medicine to dynamic list (JSON): {clean_term}")
    
    def is_medicine(self, term: str) -> bool:
        """Check if a term is in our dynamic medicine list"""
        if not term or not term.strip():
            return False
        clean_term = term.strip().lower()
        return clean_term in self.medicine_list
    
    def should_skip_term(self, term: str) -> bool:
        """Check if a term should be skipped (common words, etc.)"""
        if not term or not term.strip():
            return True
        clean_term = term.strip().lower()
        return clean_term in self.skip_words or len(clean_term) < 3
    
    def get_cached_snomed_result(self, term: str) -> Optional[Dict]:
        """Get cached spell check result for a term from the database."""
        if not term:
            return None

        if self._use_database:
            try:
                cached_result = self.db_cache.get_medical_term_cache(term)
                if cached_result:
                    # Convert DB result to the format expected by spell_checker
                    return {
                        "term": cached_result['term_text'],
                        "is_correct": cached_result['is_correct'],
                        "suggestions": [],  # Suggestions are cached separately
                        "confidence": float(cached_result['confidence_score']),
                        "source": cached_result['source'],
                        "needs_correction": cached_result['needs_correction'],
                        "category": cached_result['category']
                    }
                return None
            except Exception as e:
                print(f"⚠️ Error getting cached result from DB for '{term}': {e}")
                # Fallback to old method
                return self.cache.get(term.lower())
        else:
            # Fallback to old method
            return self.cache.get(term.lower())

    def cache_snomed_result(self, term: str, result: Dict):
        """Cache spell check results in the database."""
        if not term or not result:
            return

        if self._use_database:
            try:
                self.db_cache.set_medical_term_cache(
                    term=term,
                    is_medical=True,
                    is_correct=result.get("is_correct", False),
                    category=result.get("category", "medical"),
                    confidence_score=result.get("confidence", 0.0),
                    llm_identified='llm' in result.get("source", ""),
                    snomed_validated='snomed' in result.get("source", ""),
                    needs_correction=result.get("needs_correction", not result.get("is_correct", False)),
                    source=result.get("source", "unknown")
                )
            except Exception as e:
                print(f"⚠️ Error caching spell check result in DB for '{term}': {e}")
                # Fallback to old method
                self.cache[term.lower()] = result
                self.save_medicine_list()
        else:
            # Fallback to old method
            self.cache[term.lower()] = result
            self.save_medicine_list()
    
    def get_cached_classification(self, term: str) -> Optional[bool]:
        """Get cached LLM classification result from the database."""
        if not term:
            return None

        if self._use_database:
            try:
                cached_result = self.db_cache.get_medical_term_cache(term)
                if cached_result and cached_result.get('is_medical') is not None:
                    return cached_result['is_medical']
                return None
            except Exception as e:
                print(f"⚠️ Error getting LLM classification from DB for '{term}': {e}")
                # Fallback
                return self.classification_cache.get(term.lower())
        else:
            # Fallback
            return self.classification_cache.get(term.lower())

    def cache_classification(self, term: str, is_medical: bool):
        """Cache LLM classification result in the database."""
        if not term:
            return

        if self._use_database:
            try:
                # This is a partial result, we check if a record exists and update it, or create a new one.
                self.db_cache.set_medical_term_cache(
                    term=term,
                    is_medical=is_medical,
                    is_correct=False, # Default, not known
                    category='unknown', # Default
                    confidence_score=0.5 if is_medical else 0.0, # Some confidence
                    llm_identified=True,
                    snomed_validated=False,
                    needs_correction=False, # Not known
                    source='llm_classification'
                )
            except Exception as e:
                print(f"⚠️ Error caching LLM classification in DB for '{term}': {e}")
                # Fallback
                self.classification_cache[term.lower()] = is_medical
                self.save_medicine_list()
        else:
            # Fallback
            self.classification_cache[term.lower()] = is_medical
            self.save_medicine_list()
    
    def get_all_medicines(self) -> List[str]:
        """Get all medicines in the dynamic list"""
        return list(self.medicine_list)
    
    def get_stats(self) -> Dict:
        """Get statistics about the dynamic medicine list"""
        return {
            'total_medicines': len(self.medicine_list),
            'total_cached_results': len(self.cache),
            'total_classifications': len(self.classification_cache),
            'last_updated': datetime.now().isoformat()
        } 