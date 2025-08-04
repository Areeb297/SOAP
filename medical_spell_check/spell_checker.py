# Medical Spell Checker
"""
This module provides the main spell checking functionality for medical terms
"""

from textblob import TextBlob
from fuzzywuzzy import fuzz, process
import re
from typing import List, Dict, Tuple, Optional
from .medical_dictionary import MedicalDictionary
from .snomed_api import SnomedAPI
from .dynamic_medicine_list import DynamicMedicineList

class MedicalSpellChecker:
    def __init__(self):
        self.medical_dict = MedicalDictionary()
        self.snomed_api = SnomedAPI()
        self.dynamic_list = DynamicMedicineList()
        
        # Enhanced medical term patterns for faster detection
        self.medical_patterns = [
            # Medications (common drug suffixes)
            r'\b\w+(?:in|ol|ide|ate|ine|one|pam|lol|pril|tidine|zole|mycin|illin|profen|fen|dine)\b',
            # Medical conditions (common condition suffixes)
            r'\b\w+(?:itis|osis|emia|oma|pathy|algia|emia|osis|oma|cele|rrhagia|rrhea)\b',
            # Common medical abbreviations
            r'\b(?:BP|HR|RR|O2|CT|MRI|ECG|EKG|CBC|BMP|CMP|PT|INR|CXR|EKG|IV|PO|PRN|QID|TID|BID|QD)\b',
            # Dosage patterns
            r'\b\d+\s*(?:mg|mcg|g|ml|cc|units?|IU|mEq|mmol)\b',
            # Common medical prefixes
            r'\b(?:cardio|neuro|gastro|hepato|nephro|pulmo|dermo|endo|exo|hyper|hypo|anti|pro|pre|post)\w*\b',
            # Specific medical terms
            r'\b(?:diabetes|hypertension|asthma|pneumonia|bronchitis|sinusitis|migraine|arthritis|depression|anxiety|fever|cough|headache|nausea|vomiting|pain|swelling|bleeding|infection|inflammation)\b',
            # Drug names (common patterns)
            r'\b(?:aspirin|ibuprofen|acetaminophen|metformin|lisinopril|atorvastatin|omeprazole|simvastatin|amoxicillin|levothyroxine|metoprolol|amlodipine|losartan|hydrochlorothiazide|furosemide|warfarin|insulin|morphine|oxycodone|tramadol)\b'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.medical_patterns]
        
        # Smart skip words (expanded but focused)
        self.skip_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'mine', 'yours', 'his', 'hers', 'ours', 'theirs',
            # User's specific examples
            'online', 'decide', 'side', 'alcohol', 'wine', 'beer', 'coffee',
            'water', 'food', 'sleep', 'work', 'home', 'car', 'phone', 'computer',
            'book', 'paper', 'pen', 'table', 'chair', 'door', 'window', 'light',
            'time', 'day', 'night', 'morning', 'evening', 'afternoon'
        }
    
    def identify_medical_terms(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Identify potential medical terms in the text using fast pattern matching
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples (term, start_pos, end_pos)
        """
        medical_terms = []
        
        # First, use pattern matching for fast detection
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                term = match.group()
                # Skip if it's a common word
                if term.lower() in self.skip_words:
                    continue
                medical_terms.append((term, match.start(), match.end()))
        
        # Then check individual words that might be missed by patterns
        words = re.findall(r'\b\w+\b', text)
        
        for word in words:
            # Skip common words and short terms
            if self.dynamic_list.should_skip_term(word) or word.lower() in self.skip_words:
                continue
                
            # Check if it's in our dynamic medicine list
            if self.dynamic_list.is_medicine(word):
                # Find all occurrences of this word
                for match in re.finditer(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE):
                    medical_terms.append((match.group(), match.start(), match.end()))
                continue
            
            # Check if it's in our local medical dictionary
            if self.medical_dict.is_medical_term(word):
                # Find all occurrences of this word
                for match in re.finditer(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE):
                    medical_terms.append((match.group(), match.start(), match.end()))
                continue
        
        # Sort by position and remove duplicates
        medical_terms.sort(key=lambda x: x[1])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term, start, end in medical_terms:
            term_key = (term.lower(), start, end)
            if term_key not in seen:
                seen.add(term_key)
                unique_terms.append((term, start, end))
        
        return unique_terms
    
    def check_spelling(self, term: str) -> Dict[str, any]:
        """
        Check if a medical term is spelled correctly
        
        Args:
            term: The term to check
            
        Returns:
            Dictionary with spell check results
        """
        result = {
            "term": term,
            "is_correct": False,
            "suggestions": [],
            "confidence": 0.0,
            "source": None
        }
        
        # First, check our dynamic medicine list
        if self.dynamic_list.is_medicine(term):
            result["is_correct"] = True
            result["confidence"] = 1.0
            result["source"] = "dynamic_list"
            return result
        
        # Check our local dictionary
        if self.medical_dict.is_medical_term(term):
            correct_spelling = self.medical_dict.get_correct_spelling(term)
            if correct_spelling.lower() == term.lower():
                result["is_correct"] = True
                result["confidence"] = 1.0
                result["source"] = "local_dictionary"
            else:
                result["is_correct"] = False
                result["suggestions"] = [correct_spelling]
                result["confidence"] = 0.9
                result["source"] = "local_dictionary"
            return result
        
        # Check cached SNOMED results first
        cached_result = self.dynamic_list.get_cached_snomed_result(term)
        if cached_result:
            result.update(cached_result)
            return result
        
        # Check with SNOMED CT (with timeout and error handling)
        try:
            if self.snomed_api.validate_term(term):
                result["is_correct"] = True
                result["confidence"] = 0.95
                result["source"] = "snomed_ct"
                # Cache the result
                self.dynamic_list.cache_snomed_result(term, result)
                return result
        except Exception as e:
            print(f"SNOMED API error for term '{term}': {e}")
        
        # Get suggestions from local dictionary
        local_suggestions = self.medical_dict.get_suggestions(term)
        
        # Get suggestions from SNOMED (with error handling)
        snomed_suggestions = []
        try:
            snomed_suggestions = self.snomed_api.get_suggestions(term, max_suggestions=3)
        except Exception as e:
            print(f"SNOMED suggestions error for term '{term}': {e}")
        
        # Combine and rank suggestions
        all_suggestions = []
        
        # Add local suggestions with higher priority
        for sugg in local_suggestions[:3]:
            all_suggestions.append({
                "term": sugg,
                "score": fuzz.ratio(term.lower(), sugg.lower()),
                "source": "local"
            })
        
        # Add SNOMED suggestions
        for sugg in snomed_suggestions[:3]:
            if not any(s["term"].lower() == sugg.lower() for s in all_suggestions):
                all_suggestions.append({
                    "term": sugg,
                    "score": fuzz.ratio(term.lower(), sugg.lower()),
                    "source": "snomed"
                })
        
        # Sort by score and filter out low-quality suggestions
        all_suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        # Only include suggestions with reasonable similarity (score > 60)
        good_suggestions = [s["term"] for s in all_suggestions if s["score"] > 60]
        
        # Extract just the terms for the result
        result["suggestions"] = good_suggestions[:5]
        
        # Try general spell checking as fallback
        if not result["suggestions"]:
            try:
                blob = TextBlob(term)
                corrected = str(blob.correct())
                if corrected.lower() != term.lower():
                    result["suggestions"] = [corrected]
                    result["source"] = "textblob"
            except:
                pass
        
        result["confidence"] = 0.7 if result["suggestions"] else 0.3
        
        # Cache the result
        self.dynamic_list.cache_snomed_result(term, result)
        
        return result
    
    def check_text(self, text: str) -> List[Dict[str, any]]:
        """
        Check spelling of all medical terms in a text
        
        Args:
            text: The text to check
            
        Returns:
            List of spell check results for each medical term
        """
        medical_terms = self.identify_medical_terms(text)
        results = []
        
        for term, start, end in medical_terms:
            spell_result = self.check_spelling(term)
            spell_result["start_pos"] = start
            spell_result["end_pos"] = end
            results.append(spell_result)
        
        return results
    
    def add_medicine_to_dynamic_list(self, term: str):
        """Add a medicine term to the dynamic list"""
        self.dynamic_list.add_medicine(term)
    
    def get_dynamic_list_stats(self) -> Dict:
        """Get statistics about the dynamic medicine list"""
        return self.dynamic_list.get_stats()
    
    def correct_text(self, text: str, interactive: bool = False) -> str:
        """
        Automatically correct medical terms in text
        
        Args:
            text: The text to correct
            interactive: If True, ask user to confirm corrections
            
        Returns:
            Corrected text
        """
        corrections = self.check_text(text)
        
        # Sort by position in reverse order to avoid position shifts
        corrections.sort(key=lambda x: x["start_pos"], reverse=True)
        
        corrected_text = text
        
        for correction in corrections:
            if not correction["is_correct"] and correction["suggestions"]:
                original = correction["term"]
                suggestion = correction["suggestions"][0]
                
                if interactive:
                    print(f"\nFound: '{original}'")
                    print(f"Suggestions: {', '.join(correction['suggestions'][:3])}")
                    choice = input(f"Replace with '{suggestion}'? (y/n/other): ").lower()
                    
                    if choice == 'n':
                        continue
                    elif choice not in ['y', 'yes']:
                        # User wants to enter custom correction
                        suggestion = input("Enter correction: ")
                
                # Replace in text
                start = correction["start_pos"]
                end = correction["end_pos"]
                corrected_text = corrected_text[:start] + suggestion + corrected_text[end:]
        
        return corrected_text
    
    def get_contextual_suggestions(self, term: str, context: str, position: int) -> List[str]:
        """
        Get suggestions based on the context around the term
        
        Args:
            term: The term to get suggestions for
            context: The full text context
            position: Position of the term in the context
            
        Returns:
            List of contextual suggestions
        """
        # Extract surrounding words for context
        before_text = context[:position].split()[-5:]  # 5 words before
        after_text = context[position + len(term):].split()[:5]  # 5 words after
        
        suggestions = self.check_spelling(term)["suggestions"]
        
        # If we have context clues, we could refine suggestions
        # For example, if "take" appears before, it's likely a medication
        if any(word in ["take", "taking", "prescribed", "medication"] for word in before_text):
            # Prioritize medication suggestions
            med_suggestions = []
            for sugg in suggestions:
                if self.medical_dict.is_medical_term(sugg):
                    # Check if it's in our medication list
                    if any(sugg.lower() in meds for meds in list(self.medical_dict.medical_terms.values())[:10]):
                        med_suggestions.append(sugg)
            
            if med_suggestions:
                return med_suggestions + [s for s in suggestions if s not in med_suggestions]
        
        return suggestions
