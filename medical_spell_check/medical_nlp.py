# Medical NLP Module using spaCy and scispaCy
"""
This module provides medical NLP functionality using spaCy and scispaCy models
for fast, offline medical entity recognition and classification.
"""

import spacy
from typing import List, Dict, Tuple, Set, Optional
import re

class MedicalNLP:
    def __init__(self):
        self.nlp = None
        self.ner_model = None
        self.model_loaded = False
        self.model_load_error = None
        
        # Try to load models
        self._load_models()
        
        # Medical term categories
        self.medical_categories = {
            'CHEMICAL': 'medication',
            'DISEASE': 'condition', 
            'GENE_OR_GENOME': 'genetic',
            'SPECIES': 'organism',
            'DRUG': 'medication',
            'CONDITION': 'condition',
            'SYMPTOM': 'symptom',
            'PROCEDURE': 'procedure',
            'ANATOMY': 'anatomy',
            'TEST': 'test'
        }
        
        # Enhanced medical patterns for additional detection
        self.medical_patterns = [
            # Laboratory tests and values
            r'\b(?:HbA1c|A1C|CBC|BMP|CMP|TSH|PSA|ESR|CRP|PT|INR|PTT)\b',
            # Vital signs
            r'\b(?:BP|HR|RR|O2|temp|SpO2)\b',
            # Medical abbreviations
            r'\b(?:CT|MRI|ECG|EKG|EEG|EMG|PET|X-ray|ultrasound)\b',
            # Dosage patterns
            r'\b\d+\s*(?:mg|mcg|g|ml|cc|units?|IU|mEq|mmol)\b',
            # Medical prefixes/suffixes
            r'\b\w*(?:ology|itis|osis|emia|oma|pathy|algia|rrhagia|rrhea|scopy|tomy|ectomy)\b',
            # Common medical terms that might be missed
            r'\b(?:diagnosis|prognosis|treatment|therapy|medication|prescription|symptoms?|signs?)\b'
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.medical_patterns]
        
    def _load_models(self):
        """Load spaCy and scispaCy models"""
        try:
            # Try to load scientific model first (best for medical text)
            try:
                self.nlp = spacy.load("en_core_sci_sm")
                print("✅ Loaded en_core_sci_sm model")
            except OSError:
                # Fallback to standard English model
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    print("⚠️ Using en_core_web_sm (install en_core_sci_sm for better medical accuracy)")
                except OSError:
                    # Fallback to basic model
                    self.nlp = spacy.load('en_core_web_sm')
                    print("✅ Using en_core_web_sm model with high accuracy")
            
            # Try to load medical NER model
            try:
                self.ner_model = spacy.load("en_ner_bc5cdr_md")
                print("✅ Loaded en_ner_bc5cdr_md NER model")
            except OSError:
                print("⚠️ Medical NER model not available (install en_ner_bc5cdr_md for better entity recognition)")
                self.ner_model = None
            
            self.model_loaded = True
            
        except Exception as e:
            self.model_load_error = str(e)
            print(f"❌ Error loading spaCy models: {e}")
            self.model_loaded = False
    
    def is_available(self) -> bool:
        """Check if medical NLP is available"""
        return self.model_loaded and self.nlp is not None
    
    def get_status(self) -> Dict[str, any]:
        """Get model loading status"""
        return {
            'available': self.is_available(),
            'models': {
                'nlp': self.nlp.meta['name'] if self.nlp else None,
                'ner': self.ner_model.meta['name'] if self.ner_model else None
            },
            'error': self.model_load_error
        }
    
    def identify_medical_entities(self, text: str) -> List[Tuple[str, int, int, str, str]]:
        """
        Identify medical entities in text using spaCy models
        
        Args:
            text: The text to analyze
            
        Returns:
            List of tuples (entity, start, end, label, category)
        """
        if not self.is_available():
            return []
        
        entities = []
        
        # Process with main NLP model
        doc = self.nlp(text)
        
        # Extract entities from main model
        for ent in doc.ents:
            category = self.medical_categories.get(ent.label_, 'general')
            entities.append((ent.text, ent.start_char, ent.end_char, ent.label_, category))
        
        # Process with specialized medical NER model if available
        if self.ner_model:
            ner_doc = self.ner_model(text)
            for ent in ner_doc.ents:
                # Avoid duplicates
                existing = any(
                    abs(e[1] - ent.start_char) < 5 and abs(e[2] - ent.end_char) < 5 
                    for e in entities
                )
                if not existing:
                    category = self.medical_categories.get(ent.label_, 'medical')
                    entities.append((ent.text, ent.start_char, ent.end_char, ent.label_, category))
        
        # Add pattern-based matches
        pattern_entities = self._find_pattern_matches(text)
        entities.extend(pattern_entities)
        
        # Remove duplicates and sort by position
        entities = self._deduplicate_entities(entities)
        entities.sort(key=lambda x: x[1])  # Sort by start position
        
        return entities
    
    def _find_pattern_matches(self, text: str) -> List[Tuple[str, int, int, str, str]]:
        """Find medical terms using regex patterns"""
        entities = []
        
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                entity_text = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # Determine category based on pattern
                category = 'medical'
                label = 'MEDICAL_TERM'
                
                # Categorize based on content
                if re.search(r'\b(?:mg|mcg|g|ml|cc|units?|IU|mEq|mmol)\b', entity_text, re.IGNORECASE):
                    category = 'dosage'
                    label = 'DOSAGE'
                elif re.search(r'\b(?:HbA1c|A1C|CBC|BMP|CMP|TSH|PSA|ESR|CRP|PT|INR|PTT)\b', entity_text, re.IGNORECASE):
                    category = 'test'
                    label = 'LAB_TEST'
                elif re.search(r'\b(?:BP|HR|RR|O2|temp|SpO2)\b', entity_text, re.IGNORECASE):
                    category = 'vital_sign'
                    label = 'VITAL_SIGN'
                elif re.search(r'\b(?:CT|MRI|ECG|EKG|EEG|EMG|PET|X-ray|ultrasound)\b', entity_text, re.IGNORECASE):
                    category = 'imaging'
                    label = 'IMAGING'
                
                entities.append((entity_text, start_pos, end_pos, label, category))
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Tuple[str, int, int, str, str]]) -> List[Tuple[str, int, int, str, str]]:
        """Remove duplicate entities based on position overlap"""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda x: x[1])
        
        deduplicated = []
        for entity in entities:
            # Check for overlap with existing entities
            overlaps = False
            for existing in deduplicated:
                # Check if there's significant overlap
                overlap_start = max(entity[1], existing[1])
                overlap_end = min(entity[2], existing[2])
                overlap_length = max(0, overlap_end - overlap_start)
                
                entity_length = entity[2] - entity[1]
                existing_length = existing[2] - existing[1]
                
                # If overlap is more than 50% of either entity, consider it a duplicate
                if overlap_length > 0.5 * min(entity_length, existing_length):
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated
    
    def is_medical_term(self, term: str, context: str = "") -> Dict[str, any]:
        """
        Determine if a term is medical using NLP analysis
        
        Args:
            term: The term to check
            context: Optional context for better analysis
            
        Returns:
            Dictionary with classification results
        """
        if not self.is_available():
            return {
                'is_medical': False,
                'confidence': 0.0,
                'category': 'unknown',
                'source': 'nlp_unavailable'
            }
        
        # Analyze the term in context
        test_text = f"{context} {term}" if context else term
        entities = self.identify_medical_entities(test_text)
        
        # Check if the term appears in identified entities
        term_lower = term.lower()
        for entity_text, start, end, label, category in entities:
            if term_lower in entity_text.lower() or entity_text.lower() in term_lower:
                return {
                    'is_medical': True,
                    'confidence': 0.9,
                    'category': category,
                    'label': label,
                    'source': 'spacy_nlp'
                }
        
        # Check with individual term analysis
        doc = self.nlp(term)
        
        # Check part-of-speech and dependency patterns
        has_medical_pos = any(
            token.pos_ in ['NOUN', 'PROPN'] and token.is_alpha 
            for token in doc
        )
        
        # Check for medical-like morphology
        has_medical_morphology = any(
            token.text.lower().endswith(suffix) 
            for token in doc 
            for suffix in ['itis', 'osis', 'emia', 'oma', 'pathy', 'algia', 'scopy', 'tomy', 'ectomy']
        )
        
        if has_medical_pos and (has_medical_morphology or len(term) > 6):
            return {
                'is_medical': True,
                'confidence': 0.6,
                'category': 'potential_medical',
                'source': 'morphology_analysis'
            }
        
        return {
            'is_medical': False,
            'confidence': 0.8,
            'category': 'non_medical',
            'source': 'spacy_analysis'
        }
    
    def batch_classify_terms(self, terms: List[str], context: str = "") -> Dict[str, Dict[str, any]]:
        """
        Classify multiple terms efficiently in batch
        
        Args:
            terms: List of terms to classify
            context: Optional context for better analysis
            
        Returns:
            Dictionary mapping term to classification result
        """
        if not self.is_available():
            return {term: {'is_medical': False, 'confidence': 0.0, 'source': 'nlp_unavailable'} for term in terms}
        
        # Create a text with all terms for batch processing
        test_text = context + " " + " ".join(terms) if context else " ".join(terms)
        entities = self.identify_medical_entities(test_text)
        
        results = {}
        
        for term in terms:
            term_lower = term.lower()
            found_medical = False
            
            # Check if term matches any identified entity
            for entity_text, start, end, label, category in entities:
                entity_lower = entity_text.lower()
                if (term_lower in entity_lower or entity_lower in term_lower) and len(term) > 2:
                    results[term] = {
                        'is_medical': True,
                        'confidence': 0.9,
                        'category': category,
                        'label': label,
                        'source': 'batch_spacy_nlp'
                    }
                    found_medical = True
                    break
            
            if not found_medical:
                results[term] = {
                    'is_medical': False,
                    'confidence': 0.8,
                    'category': 'non_medical',
                    'source': 'batch_analysis'
                }
        
        return results