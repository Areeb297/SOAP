# Dynamic Medicine List
"""
This module provides a dynamic, self-growing medicine list that learns from user interactions
and serves as a primary filter before calling SNOMED CT API.
"""

import json
import os
from typing import Set, List, Dict, Optional
from datetime import datetime

class DynamicMedicineList:
    def __init__(self, storage_file: str = "dynamic_medicine_list.json"):
        self.storage_file = storage_file
        self.medicine_list: Set[str] = set()
        self.cache: Dict[str, Dict] = {}  # SNOMED cache
        self.classification_cache: Dict[str, bool] = {}  # LLM classification cache
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
    
    def add_medicine(self, term: str):
        """Add a medicine term to the dynamic list"""
        if term and term.strip():
            clean_term = term.strip().lower()
            if clean_term not in self.medicine_list and clean_term not in self.skip_words:
                self.medicine_list.add(clean_term)
                self.save_medicine_list()
                print(f"Added medicine to dynamic list: {clean_term}")
    
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
    
    def get_cached_snomed_result(self, term: str) -> Dict:
        """Get cached SNOMED result for a term"""
        return self.cache.get(term.lower(), {})
    
    def cache_snomed_result(self, term: str, result: Dict):
        """Cache SNOMED result for a term"""
        self.cache[term.lower()] = result
        self.save_medicine_list()
    
    def get_cached_classification(self, term: str) -> Optional[bool]:
        """Get cached LLM classification result for a term"""
        return self.classification_cache.get(term.lower())
    
    def cache_classification(self, term: str, is_medical: bool):
        """Cache LLM classification result for a term"""
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