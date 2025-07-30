#!/usr/bin/env python3
# Test the metadata extraction

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the function from app.py
from app import generate_soap_note_metadata

# Test cases
test_cases = [
    {
        "transcript": "Dr. Emily Chen: Good morning. Patient: Robert Smith, 52 years old.",
        "language": "en",
        "expected_patient": "Robert Smith",
        "expected_provider": "Dr. Emily Chen"
    },
    {
        "transcript": "د. إيميلي تشين: صباح الخير. المريض: روبرت سميث، 52 سنة.",
        "language": "ar",
        "expected_patient": "روبرت سميث",
        "expected_provider": "د. إيميلي تشين"
    },
    {
        "transcript": "Hi, I'm Dr. Johnson speaking. The patient Emma, she's 3 years old with fever.",
        "language": "en",
        "expected_patient": "Emma",
        "expected_provider": "Dr. Johnson"
    }
]

print("Testing metadata extraction...")
for i, test in enumerate(test_cases):
    print(f"\n=== Test Case {i+1} ===")
    print(f"Transcript: {test['transcript']}")
    print(f"Language: {test['language']}")
    
    result = generate_soap_note_metadata(test['transcript'], test['language'])
    
    print(f"\nExpected:")
    print(f"  Patient: {test['expected_patient']}")
    print(f"  Provider: {test['expected_provider']}")
    
    print(f"\nActual:")
    print(f"  Patient: {result['patient_name']}")
    print(f"  Provider: {result['provider_name']}")
    
    # Check if correct
    patient_match = result['patient_name'] == test['expected_patient'] or (test['expected_patient'] in result['patient_name'])
    provider_match = test['expected_provider'] in result['provider_name']
    
    print(f"\nResult: {'PASS' if patient_match and provider_match else 'FAIL'}")
    if not patient_match:
        print(f"  ❌ Patient name mismatch")
    if not provider_match:
        print(f"  ❌ Provider name mismatch")
