#!/usr/bin/env python3
"""
Test script to verify SOAP generation is working correctly after the fix.
This will test the /generate-soap endpoint with a sample transcript.
"""

import requests
import json
import sys

def test_soap_generation():
    """Test SOAP generation with a sample medical transcript"""
    
    # Sample medical transcript for testing
    sample_transcript = """
    Dr. Smith: Good morning, Sarah. How are you feeling today?
    
    Patient: Hi Dr. Smith. I'm Sarah Johnson, I'm 35 years old. I've been having chest pain for the past 3 days. It started suddenly while I was at work. The pain is sharp and gets worse when I take deep breaths. I also feel short of breath sometimes.
    
    Dr. Smith: I see. Have you had any fever or sweating?
    
    Patient: Yes, I had a low-grade fever yesterday, around 100.2°F. I've been sweating more than usual, especially at night.
    
    Dr. Smith: Any past medical history I should know about?
    
    Patient: I have high blood pressure, and I take lisinopril 10mg once daily. No allergies to medications. My father had heart disease.
    
    Dr. Smith: Let me examine you. Your blood pressure is 140/90, heart rate is 95, temperature is 99.8°F. On examination, your lungs are clear, heart sounds are normal.
    
    Dr. Smith: Based on your symptoms, I'm concerned about possible pleurisy or chest wall inflammation. I'd like to order a chest X-ray and some blood work including CBC and inflammatory markers.
    
    Patient: What should I do in the meantime?
    
    Dr. Smith: I'm prescribing ibuprofen 400mg three times daily for the inflammation and pain. Avoid strenuous activity. If the chest pain worsens or you develop severe shortness of breath, go to the emergency room immediately. Follow up with me in 3 days or sooner if symptoms worsen.
    
    Patient: Thank you, Dr. Smith.
    """
    
    # Test data
    test_data = {
        "transcript": sample_transcript,
        "language": "en"
    }
    
    print("Testing SOAP generation...")
    print(f"Transcript length: {len(sample_transcript)} characters")
    print("=" * 50)
    
    try:
        # Make request to the Flask server
        response = requests.post(
            "http://localhost:5000/generate-soap",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            soap_note = result.get('soapNote', {})
            
            print("✅ SOAP generation successful!")
            print(f"Message: {result.get('message', 'No message')}")
            print("=" * 50)
            
            # Check if we have the expected structure
            if 'soap_note' in soap_note:
                inner = soap_note['soap_note']
                
                print("📋 SOAP Note Structure Check:")
                print(f"  Patient Name: {inner.get('patient_name', 'Missing')}")
                print(f"  Patient Age: {inner.get('patient_age', 'Missing')}")
                print(f"  Provider: {inner.get('provider_name', 'Missing')}")
                print(f"  Visit Date: {inner.get('visit_date', 'Missing')}")
                print()
                
                # Check each section for content
                sections = ['subjective', 'objective', 'assessment', 'plan']
                for section in sections:
                    section_data = inner.get(section, {})
                    if isinstance(section_data, dict):
                        non_empty_fields = []
                        for key, value in section_data.items():
                            if value and str(value).strip():
                                if isinstance(value, list) and len(value) > 0:
                                    non_empty_fields.append(f"{key}: {len(value)} items")
                                elif isinstance(value, dict):
                                    non_empty_count = sum(1 for v in value.values() if v and str(v).strip())
                                    if non_empty_count > 0:
                                        non_empty_fields.append(f"{key}: {non_empty_count} fields")
                                else:
                                    content_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                                    non_empty_fields.append(f"{key}: {content_preview}")
                        
                        status = "✅ HAS CONTENT" if non_empty_fields else "❌ EMPTY"
                        print(f"  {section.upper()}: {status}")
                        for field in non_empty_fields[:3]:  # Show first 3 fields
                            print(f"    - {field}")
                        if len(non_empty_fields) > 3:
                            print(f"    - ... and {len(non_empty_fields) - 3} more")
                    else:
                        print(f"  {section.upper()}: ❌ INVALID STRUCTURE")
                    print()
                
                # Save the result for inspection
                with open('test_soap_result.json', 'w', encoding='utf-8') as f:
                    json.dump(soap_note, f, indent=2, ensure_ascii=False)
                print("💾 Full SOAP note saved to 'test_soap_result.json'")
                
                return True
            else:
                print("❌ Invalid SOAP note structure - missing 'soap_note' key")
                print(f"Response: {json.dumps(result, indent=2)}")
                return False
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask server at http://localhost:5000")
        print("Make sure the Flask server is running with: python app.py")
        return False
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    print("SOAP Generation Test")
    print("=" * 50)
    success = test_soap_generation()
    
    if success:
        print("\n🎉 Test completed successfully! SOAP generation is working.")
        sys.exit(0)
    else:
        print("\n💥 Test failed! There may still be issues with SOAP generation.")
        sys.exit(1)
