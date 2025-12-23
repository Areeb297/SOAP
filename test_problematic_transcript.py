#!/usr/bin/env python3
"""
Test script to debug SOAP generation issues with the user's problematic transcript.
This will help identify why the enhanced prompts aren't working.
"""

import json
import requests
import sys
from datetime import datetime

# The problematic transcript from the user
PROBLEMATIC_TRANSCRIPT = """
Patient: Sarah Johnson, 28 years old, presents with chest pain that started 3 hours ago. The pain is sharp, located in the center of her chest, and worsens with deep breathing. She went hiking last weekend and has been under stress lately, which has caused cold sores to appear. She has no known allergies and is not currently taking any medications.

Dr. Smith examined the patient and found her vital signs to be stable. Heart rate is 85 bpm, blood pressure 120/80 mmHg. Physical examination reveals tenderness over the chest wall.

Assessment: The patient likely has costochondritis, possibly related to physical activity from hiking.

Plan: Prescribed ceftriaxone 1g IV daily, pentoxifylline 400mg twice daily, gabapentin enacarbil 600mg at bedtime, doxycycline 100mg twice daily, and valacyclovir 500mg twice daily for cold sores. Patient education provided about avoiding strenuous activities. Follow-up in one week.
"""

def test_soap_generation():
    """Test SOAP generation with the problematic transcript"""
    print("="*60)
    print("TESTING SOAP GENERATION WITH PROBLEMATIC TRANSCRIPT")
    print("="*60)
    
    print(f"\nTranscript being tested:")
    print("-" * 40)
    print(PROBLEMATIC_TRANSCRIPT)
    print("-" * 40)
    
    # Test data
    test_data = {
        "transcript": PROBLEMATIC_TRANSCRIPT,
        "language": "en"
    }
    
    try:
        print(f"\nSending request to Flask backend...")
        response = requests.post(
            "http://localhost:5000/generate-soap",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            soap_note = result.get('soapNote', {})
            
            print(f"\n{'='*60}")
            print("SOAP GENERATION SUCCESSFUL")
            print(f"{'='*60}")
            
            # Check the specific issues mentioned by the user
            print(f"\n🔍 CHECKING FOR SPECIFIC ISSUES:")
            print("-" * 40)
            
            # 1. Patient name extraction
            patient_name = soap_note.get('soap_note', {}).get('patient_name', 'NOT FOUND')
            print(f"1. Patient Name: '{patient_name}'")
            if patient_name.lower() in ['not great', 'unknown', 'not mentioned']:
                print(f"   ❌ ISSUE: Patient name not properly extracted")
            elif 'sarah johnson' in patient_name.lower():
                print(f"   ✅ GOOD: Patient name properly extracted")
            else:
                print(f"   ⚠️  PARTIAL: Patient name extracted but may not be complete")
            
            # 2. Provider name extraction
            provider_name = soap_note.get('soap_note', {}).get('provider_name', 'NOT FOUND')
            print(f"2. Provider Name: '{provider_name}'")
            if 'smith' in provider_name.lower():
                print(f"   ✅ GOOD: Provider name properly extracted")
            else:
                print(f"   ⚠️  ISSUE: Provider name not properly extracted")
            
            # 3. Check for prescribed medications
            plan = soap_note.get('soap_note', {}).get('plan', {})
            medications_prescribed = plan.get('medications_prescribed', [])
            print(f"3. Prescribed Medications ({len(medications_prescribed)} found):")
            
            expected_meds = ['ceftriaxone', 'pentoxifylline', 'gabapentin enacarbil', 'doxycycline', 'valacyclovir']
            found_meds = []
            
            for med in medications_prescribed:
                med_name = med.get('name', '').lower()
                print(f"   - {med.get('name', 'Unknown')} ({med.get('dosage', 'No dosage')})")
                found_meds.append(med_name)
            
            missing_meds = [med for med in expected_meds if not any(med in found_med for found_med in found_meds)]
            if missing_meds:
                print(f"   ❌ MISSING MEDICATIONS: {missing_meds}")
            else:
                print(f"   ✅ GOOD: All expected medications found")
            
            # 4. Check social history
            subjective = soap_note.get('soap_note', {}).get('subjective', {})
            social_history = subjective.get('social_history', '').lower()
            print(f"4. Social History: '{social_history[:100]}...' (truncated)")
            
            if 'hiking' in social_history and 'stress' in social_history:
                print(f"   ✅ GOOD: Social history includes hiking and stress")
            elif 'hiking' in social_history:
                print(f"   ⚠️  PARTIAL: Hiking mentioned but stress may be missing")
            elif 'stress' in social_history:
                print(f"   ⚠️  PARTIAL: Stress mentioned but hiking may be missing")
            else:
                print(f"   ❌ ISSUE: Social history missing hiking and stress details")
            
            # 5. Check vital signs
            objective = soap_note.get('soap_note', {}).get('objective', {})
            vital_signs = objective.get('vital_signs', {})
            print(f"5. Vital Signs:")
            
            expected_vitals = {
                'heart_rate': '85',
                'blood_pressure': '120/80'
            }
            
            vital_issues = []
            for vital, expected in expected_vitals.items():
                actual = vital_signs.get(vital, '')
                print(f"   - {vital}: '{actual}'")
                if not actual or actual.lower() in ['unknown', 'not mentioned']:
                    vital_issues.append(vital)
            
            if vital_issues:
                print(f"   ❌ MISSING VITALS: {vital_issues}")
            else:
                print(f"   ✅ GOOD: Vital signs properly captured")
            
            # Print full SOAP note for inspection
            print(f"\n{'='*60}")
            print("FULL SOAP NOTE OUTPUT")
            print(f"{'='*60}")
            print(json.dumps(soap_note, indent=2, ensure_ascii=False))
            
            # Summary
            print(f"\n{'='*60}")
            print("ISSUE SUMMARY")
            print(f"{'='*60}")
            issues_found = []
            if patient_name.lower() in ['not great', 'unknown', 'not mentioned']:
                issues_found.append("Patient name extraction")
            if missing_meds:
                issues_found.append(f"Missing medications: {missing_meds}")
            if not ('hiking' in social_history and 'stress' in social_history):
                issues_found.append("Social history incomplete")
            if vital_issues:
                issues_found.append(f"Missing vital signs: {vital_issues}")
            
            if issues_found:
                print(f"❌ ISSUES FOUND:")
                for issue in issues_found:
                    print(f"   - {issue}")
                print(f"\n💡 The enhanced prompts may not be working as expected.")
                print(f"   This suggests the issue might be with:")
                print(f"   1. OpenAI model not following the detailed instructions")
                print(f"   2. Prompt structure or formatting")
                print(f"   3. Token limits causing truncation")
                print(f"   4. Model temperature settings")
            else:
                print(f"✅ NO MAJOR ISSUES FOUND - SOAP generation appears to be working correctly!")
            
        else:
            print(f"\n❌ SOAP GENERATION FAILED")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ CONNECTION ERROR")
        print(f"Could not connect to Flask backend at http://localhost:5000")
        print(f"Make sure the Flask server is running with: python app.py")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR DURING TEST")
        print(f"Error: {str(e)}")
        return False
    
    return True

def test_metadata_extraction():
    """Test just the metadata extraction function"""
    print(f"\n{'='*60}")
    print("TESTING METADATA EXTRACTION SEPARATELY")
    print(f"{'='*60}")
    
    # Import the function directly
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import generate_soap_note_metadata
        
        metadata = generate_soap_note_metadata(PROBLEMATIC_TRANSCRIPT, "en")
        
        print(f"Extracted Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: '{value}'")
        
        # Check specific issues
        if metadata['patient_name'].lower() in ['not great', 'unknown']:
            print(f"\n❌ METADATA ISSUE: Patient name = '{metadata['patient_name']}'")
        else:
            print(f"\n✅ METADATA OK: Patient name = '{metadata['patient_name']}'")
            
    except Exception as e:
        print(f"Error testing metadata extraction: {str(e)}")

if __name__ == "__main__":
    print(f"Starting SOAP generation test at {datetime.now()}")
    
    # Test metadata extraction first
    test_metadata_extraction()
    
    # Test full SOAP generation
    success = test_soap_generation()
    
    if success:
        print(f"\n✅ Test completed successfully")
    else:
        print(f"\n❌ Test failed")
        sys.exit(1)
