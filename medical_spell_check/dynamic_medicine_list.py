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
    
    def load_medicine_list(self):
        """Load the dynamic medicine list from disk"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.medicine_list = set(data.get('medicines', []))
                    self.cache = data.get('cache', {})
                    self.classification_cache = data.get('classification_cache', {})
                print(f"Loaded {len(self.medicine_list)} medicines from dynamic list")
        except Exception as e:
            print(f"Error loading dynamic medicine list: {e}")
            self.medicine_list = set()
            self.cache = {}
            self.classification_cache = {}
    
    def save_medicine_list(self):
        """Save the dynamic medicine list to disk"""
        try:
            data = {
                'medicines': list(self.medicine_list),
                'cache': self.cache,
                'classification_cache': self.classification_cache,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving dynamic medicine list: {e}")
    
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