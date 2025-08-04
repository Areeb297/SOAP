# Medical Dictionary for common medical terms and medications
"""
This module contains a comprehensive medical dictionary with common medical terms,
drug names, symptoms, conditions, and their common misspellings.
"""

import json
import os

class MedicalDictionary:
    def __init__(self):
        self.medical_terms = {
            # Common medications
            "acetaminophen": ["acitaminohen", "acetominofen", "acetaminofen", "tylenol"],
            "ibuprofen": ["ibuprofin", "ibuprophen", "ibuprofen", "advil", "motrin"],
            "aspirin": ["asprin", "aspirine", "asiprin"],
            "amoxicillin": ["amoxicilin", "amoxacillin", "amoxycillin"],
            "metformin": ["metaformin", "metformine", "glucophage"],
            "lisinopril": ["lisinoprill", "lysinopril", "lisnopril"],
            "atorvastatin": ["atorvastatin", "lipitor", "atorvastatine"],
            "levothyroxine": ["levothyroxin", "synthroid", "levothyroxine"],
            "omeprazole": ["omeprazol", "prilosec", "omeprazole"],
            "simvastatin": ["simvastatine", "zocor", "simvastatin"],
            
            # Common symptoms
            "cough": ["cof", "cogh", "coughf", "coughing"],
            "fever": ["fever", "fevar", "feaver", "pyrexia"],
            "headache": ["hedache", "headach", "cephalalgia"],
            "nausea": ["nausia", "nausea", "naushea"],
            "vomiting": ["vomitting", "vomiting", "emesis"],
            "diarrhea": ["diarhea", "diarreah", "diarrhea"],
            "constipation": ["constipaton", "constipation"],
            "fatigue": ["fatique", "fatige", "tiredness"],
            "dizziness": ["dizzyness", "dizzines", "vertigo"],
            "dyspnea": ["dispnea", "dyspnoea", "shortness of breath"],
            
            # Common conditions
            "hypertension": ["hipertension", "high blood pressure", "htn"],
            "diabetes": ["diabetis", "diabeties", "dm"],
            "diabetes mellitus": ["diabetes mellitus", "diabetic", "dm"],
            "mellitus": ["melletus", "melitus", "mellitis"],
            "hyperglycemia": ["hyperglycaemia", "hyperglycemic", "hyperglycaemic", "high blood sugar"],
            "hypoglycemia": ["hypoglycaemia", "hypoglycemic", "hypoglycaemic", "low blood sugar"],
            "blood sugar": ["blood glucose", "glucose", "sugar level"],
            "asthma": ["asma", "athsma", "asthma"],
            "pneumonia": ["pnuemonia", "neumonia", "pneumonia"],
            "bronchitis": ["bronchitus", "bronkitis", "bronchitis"],
            "sinusitis": ["sinusitus", "synusitis", "sinus infection"],
            "migraine": ["migrane", "migriane", "migraine"],
            "arthritis": ["arthrites", "arthritus", "arthritis"],
            "osteoporosis": ["osteoporoses", "osteoporosis"],
            "depression": ["depresion", "deppression", "depression"],
            
            # Medical procedures
            "echocardiogram": ["ecocardiogram", "echo", "echocardiography"],
            "electrocardiogram": ["ekg", "ecg", "electrocardiograph"],
            "magnetic resonance imaging": ["mri", "magnetic resonance"],
            "computed tomography": ["ct scan", "cat scan", "ct"],
            "x-ray": ["xray", "radiograph", "x ray"],
            "ultrasound": ["ultra sound", "sonography", "us"],
            "colonoscopy": ["colonscopy", "colonoscopy"],
            "endoscopy": ["endoscopy", "gastroscopy"],
            "biopsy": ["byopsy", "biopsy"],
            "angiography": ["angiogram", "angiography"],
            
            # Laboratory tests
            "hba1c": ["hba1c", "a1c", "hemoglobin a1c", "glycated hemoglobin"],
            "hemoglobin": ["haemoglobin", "hgb", "hb"],
            "cholesterol": ["cholestrol", "lipid panel", "lipids"],
            "triglycerides": ["tryglicerides", "tg", "trigs"],
            "creatinine": ["creatinin", "cr", "serum creatinine"],
            "glucose": ["glucos", "blood glucose", "fasting glucose"],
            "thyroid": ["thyriod", "tsh", "thyroid function"],
            
            # Body parts
            "abdomen": ["abdomin", "abdoman", "belly"],
            "thorax": ["thoracks", "chest", "thorax"],
            "cervical": ["cervicle", "neck", "cervical"],
            "lumbar": ["lumbar", "lower back", "lumbr"],
            "femur": ["femer", "thigh bone", "femur"],
            "tibia": ["tibea", "shin bone", "tibia"],
            "humerus": ["humerous", "upper arm bone", "humerus"],
            "cranium": ["craneum", "skull", "cranium"],
            "clavicle": ["clavical", "collar bone", "clavicle"],
            "sternum": ["sternam", "breast bone", "sternum"]
        }
        
        # Create reverse mapping for quick lookup
        self.reverse_mapping = {}
        for correct_term, misspellings in self.medical_terms.items():
            for misspelling in misspellings:
                self.reverse_mapping[misspelling.lower()] = correct_term
            self.reverse_mapping[correct_term.lower()] = correct_term
    
    def get_correct_spelling(self, term):
        """Get the correct spelling of a term"""
        term_lower = term.lower().strip()
        return self.reverse_mapping.get(term_lower, None)
    
    def is_medical_term(self, term):
        """Check if a term is in our medical dictionary"""
        term_lower = term.lower().strip()
        return term_lower in self.reverse_mapping
    
    def get_suggestions(self, term):
        """Get spelling suggestions for a term"""
        suggestions = []
        term_lower = term.lower().strip()
        
        # First check if it's a known misspelling
        if term_lower in self.reverse_mapping:
            correct = self.reverse_mapping[term_lower]
            if correct != term_lower:
                suggestions.append(correct)
        
        # Then find similar terms using fuzzy matching
        from difflib import get_close_matches
        all_terms = list(self.medical_terms.keys())
        close_matches = get_close_matches(term_lower, all_terms, n=5, cutoff=0.6)
        
        for match in close_matches:
            if match not in suggestions:
                suggestions.append(match)
        
        return suggestions
    
    def add_custom_term(self, correct_term, misspellings=None):
        """Add a custom medical term to the dictionary"""
        if misspellings is None:
            misspellings = []
        
        self.medical_terms[correct_term.lower()] = misspellings
        self.reverse_mapping[correct_term.lower()] = correct_term.lower()
        
        for misspelling in misspellings:
            self.reverse_mapping[misspelling.lower()] = correct_term.lower()
    
    def export_dictionary(self, filepath):
        """Export the dictionary to a JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.medical_terms, f, indent=2, ensure_ascii=False)
    
    def import_dictionary(self, filepath):
        """Import additional terms from a JSON file"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                additional_terms = json.load(f)
                for term, misspellings in additional_terms.items():
                    self.add_custom_term(term, misspellings)
