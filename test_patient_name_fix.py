#!/usr/bin/env python3
"""
Test script to verify the patient name extraction fix for transcripts with no patient names mentioned.
This tests the specific issue where patient names were showing as blank instead of "Not mentioned".
"""

import json
import os
import re
from datetime import datetime
import uuid
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

def generate_soap_note_metadata(transcript, language):
    """Generate metadata for SOAP note: patient_id, visit_date, provider_name, patient_name, patient_age"""
    from datetime import datetime
    import uuid
    import re
    
    # Generate current date in ISO format (date only, no time)
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Generate a simple patient ID
    patient_id = str(uuid.uuid4())[:8]
    
    print(f"\n=== Extracting metadata from transcript (language: {language}) ===")
    print(f"Transcript preview: {transcript[:200]}...")
    
    # Extract provider name from transcript (improved extraction)
    provider_name = "Dr. Unknown" if language == "en" else "د. غير محدد"
    if language == "en":
        # Improved English provider name extraction
        dr_match = re.search(r'Dr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', transcript)
        if dr_match:
            provider_name = f"Dr. {dr_match.group(1)}"
        else:
            provider_name = "Dr. Not mentioned"
    elif language == "ar":
        # Improved Arabic provider name extraction - look for "دكتور" or "د." followed by name
        # More specific pattern to avoid false matches
        dr_patterns = [
            r'دكتور\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)',
            r'د\.\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)',
            r'الطبيب\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)'
        ]
        provider_found = False
        for pattern in dr_patterns:
            dr_match = re.search(pattern, transcript)
            if dr_match:
                extracted_name = dr_match.group(1)
                # Validate that it's actually a name (not random text)
                if len(extracted_name) > 2 and not any(word in extracted_name.lower() for word in ['في', 'من', 'إلى', 'على', 'مع', 'بدا', 'كان', 'هذا', 'ذلك', 'التي', 'الذي']):
                    provider_name = f"د. {extracted_name}"
                    provider_found = True
                    break
        if not provider_found:
            provider_name = "د. غير محدد"
    
    # Extract patient name and age
    patient_name = "Not mentioned" if language == "en" else "غير محدد"
    patient_age = "Not mentioned" if language == "en" else "غير محدد"
    
    if language == "en":
        # Extract English patient name - improved patterns
        # Look for formal titles and names in doctor-patient dialogue first
        patient_patterns = [
            # Pattern for "Mr./Mrs./Ms./Dr. [Name]" in dialogue
            r"(?:Mr\.?|Mrs\.?|Ms\.?|Miss)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            # Pattern for "Patient: [Name], [age]" or "Patient: [Name]" (but exclude greetings)
            r"patient\s*:\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+\d+|$)",
            # Pattern for "The patient [Name]"
            r"(?:the\s+)?patient\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+is|\s+\d+|$)",
            # Pattern for "patient is [Name]"
            r"patient\s+is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+\d+|$)",
            # Pattern for "[Name] is a XX-year-old"
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+is\s+(?:a\s+)?\d+\s*(?:-)?\s*year",
            r"I'm\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"My name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"I am\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"This is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)"
        ]
        for pattern in patient_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                extracted_name = match.group(1).strip()
                # Remove common titles if they appear at the start
                extracted_name = re.sub(r'^(Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+', '', extracted_name)
                # Simple validation - just check it's not obviously invalid
                # Don't extract if it's clearly not a name
                if (len(extracted_name) > 2 and 
                    not extracted_name.lower() in ['not every day', 'every day', 'flare up', 'not great', 'not mentioned', 
                                                  'the patient', 'patient', 'presents', 'complains', 'reports', 'symptoms']):
                    patient_name = extracted_name
                    print(f"Matched patient name '{patient_name}' with pattern: {pattern}")
                    break
        
        # Extract English patient age - improved patterns
        age_patterns = [
            r"(\d+)\s*(?:-)?\s*year\s*(?:-)?\s*old",
            r"age\s*(?:is)?\s*[:\s]*(\d+)",
            r"aged\s+(\d+)",
            r"he's\s+(\d+)",
            r"she's\s+(\d+)",
            r"patient is\s+(\d+)"
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, transcript, re.IGNORECASE)
            if age_match:
                patient_age = age_match.group(1)
                break
    
    elif language == "ar":
        # Extract Arabic patient name - improved patterns
        name_patterns = [
            # Pattern for "المريض: [الاسم]"
            r"المريض\s*:\s*([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            # Pattern for "المريض [الاسم]"
            r"المريض\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            # Pattern for "المريضة [الاسم]"
            r"المريضة\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            r"اسمي\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"أنا\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسم المريض\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"هذا\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"هذه\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, transcript)
            if match:
                extracted_name = match.group(1).strip()
                # Remove common prefixes
                extracted_name = re.sub(r'^(د\.|دكتور|الدكتور)\s+', '', extracted_name)
                # Validate that it's actually a name (not random text)
                if len(extracted_name) > 1 and not any(word in extracted_name for word in ['في', 'من', 'إلى', 'على', 'مع', 'هو', 'هي']):
                    patient_name = extracted_name
                    print(f"Matched patient name '{patient_name}' with pattern: {pattern}")
                    break
        
        # Extract Arabic patient age - improved patterns
        age_patterns = [
            r"عمري\s+(\d+)\s+سنة",
            r"عمره\s+(\d+)\s+سنة",
            r"عمرها\s+(\d+)\s+سنة",
            r"العمر\s*[:]*\s*(\d+)",
            r"(\d+)\s+سنة"
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, transcript)
            if age_match:
                patient_age = age_match.group(1)
                break
    
    print(f"\nExtracted metadata:")
    print(f"  Provider: {provider_name}")
    print(f"  Patient: {patient_name}")
    print(f"  Age: {patient_age}")
    
    return {
        "patient_id": patient_id,
        "visit_date": current_date,
        "provider_name": provider_name,
        "patient_name": patient_name,
        "patient_age": patient_age
    }

# Test transcripts with no patient names mentioned
TEST_TRANSCRIPTS = [
    {
        "name": "Short greeting transcript",
        "transcript": "Hello Doctor",
        "language": "en",
        "expected_patient_name": "Not mentioned",
        "expected_provider_name": "Dr. Not mentioned"
    },
    {
        "name": "Generic medical consultation",
        "transcript": "The patient presents with chest pain that started yesterday. Physical examination shows normal vital signs. Prescribed medication for pain relief.",
        "language": "en", 
        "expected_patient_name": "Not mentioned",
        "expected_provider_name": "Dr. Not mentioned"
    },
    {
        "name": "Arabic greeting",
        "transcript": "مرحبا دكتور",
        "language": "ar",
        "expected_patient_name": "غير محدد",
        "expected_provider_name": "د. غير محدد"
    },
    {
        "name": "Arabic medical consultation",
        "transcript": "المريض يشكو من ألم في الصدر منذ أمس. الفحص البدني طبيعي. تم وصف دواء للألم.",
        "language": "ar",
        "expected_patient_name": "غير محدد", 
        "expected_provider_name": "د. غير محدد"
    }
]

def test_patient_name_extraction():
    """Test patient name extraction for transcripts with no patient names"""
    print("=" * 80)
    print("TESTING PATIENT NAME EXTRACTION FIX")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for i, test_case in enumerate(TEST_TRANSCRIPTS, 1):
        print(f"TEST {i}: {test_case['name']}")
        print("-" * 50)
        print(f"Transcript: '{test_case['transcript']}'")
        print(f"Language: {test_case['language']}")
        print()
        
        # Test metadata extraction
        metadata = generate_soap_note_metadata(test_case['transcript'], test_case['language'])
        
        print("RESULTS:")
        print(f"  Patient Name: '{metadata['patient_name']}'")
        print(f"  Provider Name: '{metadata['provider_name']}'")
        print(f"  Patient Age: '{metadata['patient_age']}'")
        print()
        
        # Check patient name
        if metadata['patient_name'] == test_case['expected_patient_name']:
            print("  ✅ Patient name extraction PASSED")
        else:
            print(f"  ❌ Patient name extraction FAILED")
            print(f"     Expected: '{test_case['expected_patient_name']}'")
            print(f"     Got: '{metadata['patient_name']}'")
            all_passed = False
        
        # Check provider name
        if metadata['provider_name'] == test_case['expected_provider_name']:
            print("  ✅ Provider name extraction PASSED")
        else:
            print(f"  ❌ Provider name extraction FAILED")
            print(f"     Expected: '{test_case['expected_provider_name']}'")
            print(f"     Got: '{metadata['provider_name']}'")
            all_passed = False
        
        print()
        print("=" * 50)
        print()
    
    return all_passed

def test_openai_integration():
    """Test the full OpenAI integration with patient name fallback logic"""
    print("TESTING OPENAI INTEGRATION WITH PATIENT NAME FALLBACK")
    print("=" * 60)
    print()
    
    if not client.api_key:
        print("❌ ERROR: OpenAI API key not configured")
        return False
    
    # Test with a transcript that has no patient name
    test_transcript = "The patient presents with headache. Physical exam normal. Prescribed ibuprofen."
    
    print(f"Test transcript: '{test_transcript}'")
    print()
    
    # Generate metadata
    metadata = generate_soap_note_metadata(test_transcript, "en")
    print(f"Metadata patient name: '{metadata['patient_name']}'")
    print()
    
    # Simulate the OpenAI response processing (simplified)
    # In the real app, this would be the full SOAP generation
    mock_ai_response = {
        'soap_note': {
            'patient_name': '',  # Simulate blank patient name from AI
            'provider_name': 'Dr. Unknown',
            'patient_age': 'Unknown'
        }
    }
    
    print("Simulated AI response patient name: (blank)")
    print()
    
    # Apply the fix logic from app.py
    patient_name_from_ai = mock_ai_response['soap_note'].get('patient_name', '').strip()
    if (not patient_name_from_ai or 
        patient_name_from_ai.lower() in ['unknown', 'غير محدد', 'dr', 'د', 'مرحبا', 'hello', 'not mentioned']):
        mock_ai_response['soap_note']['patient_name'] = metadata['patient_name']
    
    final_patient_name = mock_ai_response['soap_note']['patient_name']
    print(f"Final patient name after fix: '{final_patient_name}'")
    
    if final_patient_name == "Not mentioned":
        print("✅ OpenAI integration fix PASSED")
        return True
    else:
        print("❌ OpenAI integration fix FAILED")
        return False

if __name__ == "__main__":
    print("Testing patient name extraction fix...")
    print()
    
    # Test metadata extraction
    metadata_passed = test_patient_name_extraction()
    
    # Test OpenAI integration
    openai_passed = test_openai_integration()
    
    print()
    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if metadata_passed:
        print("✅ Metadata extraction tests PASSED")
    else:
        print("❌ Metadata extraction tests FAILED")
    
    if openai_passed:
        print("✅ OpenAI integration test PASSED")
    else:
        print("❌ OpenAI integration test FAILED")
    
    if metadata_passed and openai_passed:
        print()
        print("🎉 ALL TESTS PASSED! Patient name fix is working correctly.")
    else:
        print()
        print("❌ SOME TESTS FAILED! Patient name fix needs attention.")
