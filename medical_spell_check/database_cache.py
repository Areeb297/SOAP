# Database Cache Manager
"""
This module provides database-backed caching for medical spell checking operations.
It manages connections to Supabase PostgreSQL and provides CRUD operations for all cache tables.
"""

import os
import json
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import time

class DatabaseCache:
    def __init__(self):
        """Initialize database cache manager with Supabase connection"""
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.connection = None
        self.is_available = False
        self._connect()
        
        print(f"Database cache initialized - Available: {self.is_available}")
    
    def _connect(self):
        """Establish database connection with error handling"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.is_available = True
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.connection = None
            self.is_available = False
    
    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        if not self.connection or self.connection.closed:
            print("Database connection lost, attempting to reconnect...")
            self._connect()
    
    def _get_cursor(self):
        """Get database cursor with connection check"""
        self._ensure_connection()
        if not self.is_available:
            return None
        try:
            return self.connection.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"Error getting cursor: {e}")
            self.is_available = False
            return None
    
    def _commit_and_close(self, cursor):
        """Commit transaction and close cursor"""
        if cursor:
            try:
                self.connection.commit()
                cursor.close()
            except Exception as e:
                print(f"Error committing transaction: {e}")
                if self.connection:
                    self.connection.rollback()
    
    def _generate_hash(self, text: str) -> str:
        """Generate SHA-256 hash for cache keys"""
        return hashlib.sha256(text.lower().strip().encode('utf-8')).hexdigest()
    
    def log_usage_stats(self, endpoint: str, operation: str, cache_hit: bool, 
                       processing_time_ms: int, error_occurred: bool = False, 
                       error_message: str = None, response_size_bytes: int = None):
        """Log API usage statistics to database"""
        if not self.is_available:
            return
        
        cursor = self._get_cursor()
        if not cursor:
            return
        
        try:
            query = """
                INSERT INTO api_usage_stats 
                (endpoint, operation, cache_hit, processing_time_ms, response_size_bytes, 
                 error_occurred, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query, (
                endpoint, operation, cache_hit, processing_time_ms, 
                response_size_bytes, error_occurred, error_message
            ))
            self._commit_and_close(cursor)
        except Exception as e:
            print(f"Error logging usage stats: {e}")
            if cursor:
                cursor.close()
    
    # ==========================================
    # MEDICAL TERM CACHE OPERATIONS
    # ==========================================
    
    def get_medical_term_cache(self, term: str) -> Optional[Dict]:
        """Get cached medical term processing result"""
        if not self.is_available:
            return None
        
        cursor = self._get_cursor()
        if not cursor:
            return None
        
        try:
            term_hash = self._generate_hash(term)
            query = """
                SELECT * FROM medical_term_cache 
                WHERE term_hash = %s
            """
            cursor.execute(query, (term_hash,))
            result = cursor.fetchone()
            
            if result:
                # Update access statistics
                update_query = """
                    UPDATE medical_term_cache 
                    SET access_count = access_count + 1, last_accessed = NOW()
                    WHERE id = %s
                """
                cursor.execute(update_query, (result['id'],))
                self._commit_and_close(cursor)
                
                # Convert to dictionary and return
                return dict(result)
            else:
                cursor.close()
                return None
                
        except Exception as e:
            print(f"Error getting medical term cache: {e}")
            if cursor:
                cursor.close()
            return None
    
    def set_medical_term_cache(self, term: str, is_medical: bool, is_correct: bool,
                              category: str, confidence_score: float, llm_identified: bool,
                              snomed_validated: bool, needs_correction: bool, 
                              source: str) -> bool:
        """Cache medical term processing result"""
        if not self.is_available:
            return False
        
        cursor = self._get_cursor()
        if not cursor:
            return False
        
        try:
            term_hash = self._generate_hash(term)
            query = """
                INSERT INTO medical_term_cache 
                (term_text, term_hash, is_medical, is_correct, category, confidence_score,
                 llm_identified, snomed_validated, needs_correction, source, created_at, last_accessed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (term_hash) DO UPDATE SET
                    is_medical = EXCLUDED.is_medical,
                    is_correct = EXCLUDED.is_correct,
                    category = EXCLUDED.category,
                    confidence_score = EXCLUDED.confidence_score,
                    llm_identified = EXCLUDED.llm_identified,
                    snomed_validated = EXCLUDED.snomed_validated,
                    needs_correction = EXCLUDED.needs_correction,
                    source = EXCLUDED.source,
                    last_accessed = NOW(),
                    access_count = medical_term_cache.access_count + 1
            """
            cursor.execute(query, (
                term, term_hash, is_medical, is_correct, category, confidence_score,
                llm_identified, snomed_validated, needs_correction, source
            ))
            self._commit_and_close(cursor)
            return True
            
        except Exception as e:
            print(f"Error setting medical term cache: {e}")
            if cursor:
                cursor.close()
            return False
    
    # ==========================================
    # SNOMED API CACHE OPERATIONS
    # ==========================================
    
    def get_snomed_cache(self, search_term: str) -> Optional[Dict]:
        """Get cached SNOMED API response"""
        if not self.is_available:
            return None
        
        cursor = self._get_cursor()
        if not cursor:
            return None
        
        try:
            search_hash = self._generate_hash(search_term)
            query = """
                SELECT * FROM snomed_api_cache 
                WHERE search_hash = %s AND expires_at > NOW()
            """
            cursor.execute(query, (search_hash,))
            result = cursor.fetchone()
            cursor.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error getting SNOMED cache: {e}")
            if cursor:
                cursor.close()
            return None
    
    def set_snomed_cache(self, search_term: str, api_response: Dict, 
                        concept_count: int, is_valid: bool, response_time_ms: int) -> bool:
        """Cache SNOMED API response"""
        if not self.is_available:
            return False
        
        cursor = self._get_cursor()
        if not cursor:
            return False
        
        try:
            search_hash = self._generate_hash(search_term)
            query = """
                INSERT INTO snomed_api_cache 
                (search_term, search_hash, api_response, concept_count, is_valid, 
                 response_time_ms, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '24 hours')
                ON CONFLICT (search_hash) DO UPDATE SET
                    api_response = EXCLUDED.api_response,
                    concept_count = EXCLUDED.concept_count,
                    is_valid = EXCLUDED.is_valid,
                    response_time_ms = EXCLUDED.response_time_ms,
                    created_at = NOW(),
                    expires_at = NOW() + INTERVAL '24 hours'
            """
            cursor.execute(query, (
                search_term, search_hash, json.dumps(api_response), 
                concept_count, is_valid, response_time_ms
            ))
            self._commit_and_close(cursor)
            return True
            
        except Exception as e:
            print(f"Error setting SNOMED cache: {e}")
            if cursor:
                cursor.close()
            return False
    
    # ==========================================
    # SPELL SUGGESTION CACHE OPERATIONS
    # ==========================================
    
    def get_spell_suggestion_cache(self, original_term: str) -> Optional[Dict]:
        """Get cached spell check suggestions"""
        if not self.is_available:
            return None
        
        cursor = self._get_cursor()
        if not cursor:
            return None
        
        try:
            original_hash = self._generate_hash(original_term)
            query = """
                SELECT * FROM spell_suggestion_cache 
                WHERE original_hash = %s AND expires_at > NOW()
                ORDER BY confidence_score DESC
                LIMIT 1
            """
            cursor.execute(query, (original_hash,))
            result = cursor.fetchone()
            
            if result:
                # Update access count
                update_query = """
                    UPDATE spell_suggestion_cache 
                    SET access_count = access_count + 1
                    WHERE id = %s
                """
                cursor.execute(update_query, (result['id'],))
                self._commit_and_close(cursor)
                return dict(result)
            else:
                cursor.close()
                return None
                
        except Exception as e:
            print(f"Error getting spell suggestion cache: {e}")
            if cursor:
                cursor.close()
            return None
    
    def set_spell_suggestion_cache(self, original_term: str, suggested_terms: List[Dict],
                                  suggestion_source: str, confidence_score: float) -> bool:
        """Cache spell check suggestions"""
        if not self.is_available:
            return False
        
        cursor = self._get_cursor()
        if not cursor:
            return False
        
        try:
            original_hash = self._generate_hash(original_term)
            query = """
                INSERT INTO spell_suggestion_cache 
                (original_term, original_hash, suggested_terms, suggestion_source,
                 suggestion_count, confidence_score, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '7 days')
                ON CONFLICT (original_hash) DO UPDATE SET
                    suggested_terms = EXCLUDED.suggested_terms,
                    suggestion_source = EXCLUDED.suggestion_source,
                    suggestion_count = EXCLUDED.suggestion_count,
                    confidence_score = EXCLUDED.confidence_score,
                    created_at = NOW(),
                    expires_at = NOW() + INTERVAL '7 days',
                    access_count = spell_suggestion_cache.access_count + 1
            """
            cursor.execute(query, (
                original_term, original_hash, json.dumps(suggested_terms),
                suggestion_source, len(suggested_terms), confidence_score
            ))
            self._commit_and_close(cursor)
            return True
            
        except Exception as e:
            print(f"Error setting spell suggestion cache: {e}")
            if cursor:
                cursor.close()
            return False
    
    # ==========================================
    # LLM PROCESSING CACHE OPERATIONS
    # ==========================================
    
    def get_llm_cache(self, text_input: str) -> Optional[Dict]:
        """Get cached LLM processing result"""
        if not self.is_available:
            return None
        
        cursor = self._get_cursor()
        if not cursor:
            return None
        
        try:
            text_hash = self._generate_hash(text_input)
            query = """
                SELECT * FROM llm_processing_cache 
                WHERE text_hash = %s AND expires_at > NOW()
            """
            cursor.execute(query, (text_hash,))
            result = cursor.fetchone()
            cursor.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error getting LLM cache: {e}")
            if cursor:
                cursor.close()
            return None
    
    def set_llm_cache(self, text_input: str, llm_response: Dict, 
                     medical_terms_found: int, processing_time_ms: int,
                     model_used: str = 'gpt-4o-mini') -> bool:
        """Cache LLM processing result"""
        if not self.is_available:
            return False
        
        cursor = self._get_cursor()
        if not cursor:
            return False
        
        try:
            text_hash = self._generate_hash(text_input)
            query = """
                INSERT INTO llm_processing_cache 
                (text_input, text_hash, llm_response, medical_terms_found, 
                 processing_time_ms, model_used, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW() + INTERVAL '12 hours')
                ON CONFLICT (text_hash) DO UPDATE SET
                    llm_response = EXCLUDED.llm_response,
                    medical_terms_found = EXCLUDED.medical_terms_found,
                    processing_time_ms = EXCLUDED.processing_time_ms,
                    model_used = EXCLUDED.model_used,
                    created_at = NOW(),
                    expires_at = NOW() + INTERVAL '12 hours'
            """
            cursor.execute(query, (
                text_input, text_hash, json.dumps(llm_response),
                medical_terms_found, processing_time_ms, model_used
            ))
            self._commit_and_close(cursor)
            return True
            
        except Exception as e:
            print(f"Error setting LLM cache: {e}")
            if cursor:
                cursor.close()
            return False
    
    # ==========================================
    # MEDICINE LIST EXTENDED OPERATIONS
    # ==========================================
    
    def get_medicine_by_name(self, medicine_name: str) -> Optional[Dict]:
        """Get medicine from extended list by name"""
        if not self.is_available:
            return None
        
        cursor = self._get_cursor()
        if not cursor:
            return None
        
        try:
            query = """
                SELECT * FROM medicine_list_extended 
                WHERE medicine_name ILIKE %s OR %s = ANY(
                    SELECT jsonb_array_elements_text(common_misspellings)
                )
            """
            cursor.execute(query, (medicine_name, medicine_name.lower()))
            result = cursor.fetchone()
            
            if result:
                # Update usage count
                update_query = """
                    UPDATE medicine_list_extended 
                    SET usage_count = usage_count + 1
                    WHERE id = %s
                """
                cursor.execute(update_query, (result['id'],))
                self._commit_and_close(cursor)
                return dict(result)
            else:
                cursor.close()
                return None
                
        except Exception as e:
            print(f"Error getting medicine by name: {e}")
            if cursor:
                cursor.close()
            return None
    
    def add_medicine_to_extended_list(self, medicine_name: str, category: str = 'medication',
                                     confirmed_correct: bool = False, user_confirmed: bool = False,
                                     snomed_code: str = None, generic_name: str = None,
                                     brand_names: List[str] = None, 
                                     common_misspellings: List[str] = None) -> bool:
        """Add medicine to extended list"""
        if not self.is_available:
            return False
        
        cursor = self._get_cursor()
        if not cursor:
            return False
        
        try:
            medicine_hash = self._generate_hash(medicine_name)
            query = """
                INSERT INTO medicine_list_extended 
                (medicine_name, medicine_hash, category, confirmed_correct, user_confirmed,
                 snomed_code, generic_name, brand_names, common_misspellings, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (medicine_name) DO UPDATE SET
                    category = EXCLUDED.category,
                    confirmed_correct = EXCLUDED.confirmed_correct,
                    user_confirmed = EXCLUDED.user_confirmed,
                    snomed_code = EXCLUDED.snomed_code,
                    generic_name = EXCLUDED.generic_name,
                    brand_names = EXCLUDED.brand_names,
                    common_misspellings = EXCLUDED.common_misspellings,
                    usage_count = medicine_list_extended.usage_count + 1
            """
            cursor.execute(query, (
                medicine_name, medicine_hash, category, confirmed_correct, user_confirmed,
                snomed_code, generic_name, 
                json.dumps(brand_names) if brand_names else None,
                json.dumps(common_misspellings) if common_misspellings else None
            ))
            self._commit_and_close(cursor)
            return True
            
        except Exception as e:
            print(f"Error adding medicine to extended list: {e}")
            if cursor:
                cursor.close()
            return False
    
    # ==========================================
    # CACHE MAINTENANCE OPERATIONS
    # ==========================================
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries and return count of deleted records"""
        if not self.is_available:
            return 0
        
        cursor = self._get_cursor()
        if not cursor:
            return 0
        
        try:
            # Call the stored procedure
            cursor.execute("SELECT cleanup_expired_cache()")
            result = cursor.fetchone()
            self._commit_and_close(cursor)
            
            deleted_count = result[0] if result else 0
            print(f"Cache cleanup completed: {deleted_count} expired entries removed")
            return deleted_count
            
        except Exception as e:
            print(f"Error during cache cleanup: {e}")
            if cursor:
                cursor.close()
            return 0
    
    def get_cache_performance_stats(self) -> Dict:
        """Get cache performance statistics"""
        if not self.is_available:
            return {}
        
        cursor = self._get_cursor()
        if not cursor:
            return {}
        
        try:
            query = "SELECT * FROM cache_performance"
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            return {row['endpoint']: dict(row) for row in results}
            
        except Exception as e:
            print(f"Error getting cache performance stats: {e}")
            if cursor:
                cursor.close()
            return {}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("Database connection closed")

# Global instance for reuse
_db_cache_instance = None

def get_database_cache() -> DatabaseCache:
    """Get singleton database cache instance"""
    global _db_cache_instance
    if _db_cache_instance is None:
        try:
            _db_cache_instance = DatabaseCache()
        except Exception as e:
            print(f"Failed to initialize database cache: {e}")
            _db_cache_instance = None
    return _db_cache_instance