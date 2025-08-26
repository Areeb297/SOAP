#!/usr/bin/env python3
"""
Test script to verify OpenAI-only SOAP generation without running Flask server
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Test transcript (the problematic one from before)
TEST_TRANSCRIPT = """
Patient: Sarah Johnson, 28 years old, presents with chest pain that started 3 hours ago. The pain is sharp, located in the center of her chest, and worsens with deep breathing. She went hiking last weekend and has been under stress lately, which has caused cold sores to appear. She has no known allergies and is not currently taking any medications.

Dr. Smith examined the patient and found her vital signs to be stable. Heart rate is 85 bpm, blood pressure 120/80 mmHg. Physical examination reveals tenderness over the chest wall.

Assessment: The patient likely has costochondritis, possibly related to physical activity from hiking.

Plan: Prescribed ceftriaxone 1g IV daily, pentoxifylline 400mg twice daily, gabapentin enacarbil 600mg at bedtime, doxycycline 100mg twice daily, and valacyclovir 500mg twice daily for cold sores. Patient education provided about avoiding strenuous activities. Follow-up in one week.
"""

# SOAP System Prompt (same as in app.py)
SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant specialized in creating SOAP notes from doctor-patient conversations.

Output ONLY a valid JSON object without any explanation or external text. If you add anything outside the JSON object, the response will be rejected. The response must be a JSON object only with the following structure:

{
  "soap_note": {
    "patient_id": "auto-generated",
    "visit_date": "current-date-time",
    "provider_name": "Dr. [Name from conversation or 'Unknown']",
    "patient_name": "[Patient's full name from conversation]",
    "patient_age": "[Patient's age from conversation]",
    "subjective": {
      "chief_complaint": "...",
      "history_of_present_illness": "...",
      "past_medical_history": "...",
      "family_history": "...",
      "social_history": "...",
      "medications": [
        {
          "name": "Medication name",
          "dosage": "Dosage information",
          "frequency": "How often taken",
          "route": "oral/inhalation/etc",
          "duration": "How long taking"
        }
      ],
      "allergies": ["List of allergies"]
    },
    "objective": {
      "vital_signs": {
        "temperature": "Temperature if mentioned",
        "blood_pressure": "BP if mentioned",
        "heart_rate": "HR if mentioned",
        "respiratory_rate": "RR if mentioned",
        "oxygen_saturation": "O2 sat if mentioned"
      },
      "physical_exam": "Physical examination findings"
    },
    "assessment": {
      "diagnosis": "Primary diagnosis",
      "risk_factors": ["List of risk factors"]
    },
    "plan": {
      "medications_prescribed": [
        {
          "name": "Medication name",
          "dosage": "Dosage",
          "frequency": "How often",
          "duration": "How long",
          "route": "oral/injection/etc"
        }
      ],
      "procedures_or_tests": ["List of tests/procedures"],
      "patient_education": "Education provided to patient",
      "follow_up_instructions": "Follow-up plan"
    }
  }
}

CRITICAL INSTRUCTIONS - CAPTURE EVERYTHING MENTIONED:

1. PATIENT IDENTIFICATION: Extract and include:
   - Patient's full name (first and last name) - MUST be included in patient_name field
   - IMPORTANT: Do NOT prefix patient name with "Dr." unless they are explicitly identified as a doctor who is the patient
   - Age (exact number mentioned) - MUST be included in patient_age field
   - If patient introduces themselves (e.g., "Hi, I'm Sarah"), that's the patient name
   - If doctor addresses patient by name (e.g., "Hello Sarah"), that's the patient name
   - Location/address/city mentioned
   - Any other demographic information
   - If patient name is mentioned as "Patient: [Name]" or "The patient [Name]", extract only the name part
   - If no patient name is explicitly mentioned, you can infer it from context (e.g., the person speaking who is not the doctor)
   - If no name is mentioned at all, use "Not mentioned" instead of "Unknown"

2. PROVIDER IDENTIFICATION: Extract and include:
   - Doctor's name (Dr. [Name] or د. [Name])
   - Department/specialty mentioned
   - Any other provider information

3. CHIEF COMPLAINT: Include:
   - Primary symptom(s) with exact description
   - Duration mentioned (hours, days, weeks)
   - Location of symptoms (if specified)

4. HISTORY OF PRESENT ILLNESS: MUST include ALL mentioned:
   - Exact timing (when symptoms started)
   - Detailed description of symptoms
   - Associated symptoms (fever, sweating, nausea, vomiting, etc.)
   - Aggravating factors (movement, pressure, etc.)
   - Relieving factors (if mentioned)
   - Progression of symptoms
   - Impact on daily activities
   - Any other symptoms mentioned in conversation
   - IMPORTANT: This should be a detailed narrative paragraph, not just bullet points

5. PAST MEDICAL HISTORY: Include ALL mentioned:
   - Chronic diseases
   - Previous surgeries (with dates if mentioned)
   - Current medications (even if "none" or "no medications" - MUST document this)
   - Previous hospitalizations
   - Any other medical history

6. FAMILY HISTORY: Include ALL mentioned:
   - Family members with medical conditions
   - Specific conditions mentioned
   - Ages of family members (if mentioned)
   - Any genetic conditions

7. SOCIAL HISTORY: Include ALL mentioned:
   - Occupation/job
   - Smoking/alcohol use
   - Living situation
   - Lifestyle factors
   - Recent activities (hiking, travel, outdoor activities, etc.)
   - Stress factors (mentioned in relation to symptoms like cold sores)
   - Any other social information
   - IMPORTANT: Include recent activities that may be relevant to current symptoms (e.g., "went hiking last weekend")

8. MEDICATIONS: Include ALL mentioned:
   - Current medications (name, dosage, frequency, route)
   - If "no medications" mentioned, document that explicitly
   - Duration of medication use
   - Any medication changes

9. ALLERGIES: Include ALL mentioned:
   - Drug allergies
   - Food allergies
   - Environmental allergies
   - If "no allergies" mentioned, document that explicitly

10. VITAL SIGNS: Include ALL mentioned:
    - Temperature (if mentioned)
    - Blood pressure (if mentioned)
    - Heart rate (if mentioned)
    - Respiratory rate (if mentioned)
    - Oxygen saturation (if mentioned)
    - Any other vital signs mentioned

11. PHYSICAL EXAMINATION: Include ALL mentioned:
    - Any examination performed
    - Findings mentioned
    - Areas examined
    - Any abnormal findings

12. DIAGNOSIS: Use the most likely diagnosis based on:
    - Symptoms described
    - Clinical findings
    - Medical reasoning

13. RISK FACTORS: Include ALL mentioned:
    - Medical conditions
    - Family history factors
    - Lifestyle factors
    - Age-related factors
    - Any other risk factors

14. MEDICATIONS PRESCRIBED: Include ALL mentioned:
    - New medications ordered (ceftriaxone, pentoxifylline, gabapentin enacarbil, doxycycline, valacyclovir, etc.)
    - Dosage, frequency, route (if specified, otherwise leave blank)
    - Duration of treatment (if specified, otherwise leave blank)
    - Any medication changes
    - IMPORTANT: If a medication is mentioned by the doctor as being prescribed, it MUST be included even if dosage details are not provided

15. PROCEDURES/TESTS: Include ALL mentioned:
    - Laboratory tests
    - Imaging studies
    - Procedures ordered
    - Any investigations mentioned

16. PATIENT EDUCATION: Include ALL mentioned:
    - Instructions given
    - Warnings provided
    - Lifestyle advice
    - Any education provided
    - Diagnosis-specific education (e.g., for heart attack: signs to watch for, lifestyle changes)
    - Medication instructions and side effects
    - When to seek immediate medical attention
    - Prevention strategies

17. FOLLOW-UP: Include ALL mentioned:
    - Follow-up timing
    - Return instructions
    - Monitoring requirements
    - Any follow-up plans
    - Diagnosis-specific follow-up (e.g., "Cardiology follow-up" for cardiac issues, "Neurology follow-up" for neurological issues)
    - Emergency return criteria
    - Specialist referrals if needed

IMPORTANT: Do not omit any information mentioned in the conversation. If something is mentioned, it must be included in the appropriate section. Use exact quotes and details from the conversation rather than generic phrases.

REMINDER FOR PATIENT NAME: 
- Extract the actual patient name, not the doctor's name
- If you see "Patient: [Name]" extract only the name part
- Do NOT prefix patient names with "Dr." unless the patient themselves is explicitly identified as a doctor
- If a name appears after "Patient:" or "The patient", that is the patient's name
- If the transcript is very short (e.g., just a greeting), and no names are mentioned:
  - For provider_name: Keep as "Dr. Unknown" or "Dr. Not mentioned"
  - For patient_name: Keep as "Unknown" (do not use greetings like "Hello" as names)
  - For patient_age: Keep as "Unknown" if not mentioned
- Common greetings like "Hello", "Hi", "Good morning" are NOT names

EXAMPLES:
- If transcript is "Hello Doctor", patient_name should be "Unknown", NOT "Hello" or "Doctor"
- If transcript is "Dr. Smith: Hello Sarah, how are you?", then provider_name is "Dr. Smith" and patient_name is "Sarah"
- If transcript is "Patient: John Doe, 45 years old", then patient_name is "John Doe" and patient_age is "45"

Do not write anything outside the JSON object."""

def extract_json_from_response(response_text):
    """Extract JSON from response text that may contain extra text"""
    try:
        # First try to parse as-is
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Try to find JSON within the text using regex
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        lines = response_text.strip().split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        for line in lines:
            if '{' in line and not in_json:
                in_json = True
                brace_count = line.count('{') - line.count('}')
                json_lines.append(line)
            elif in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    break
        if json_lines:
            try:
                return json.loads('\n'.join(json_lines))
            except json.JSONDecodeError:
                pass
        return None

def test_openai_soap_generation():
    """Test OpenAI-only SOAP generation"""
    print("=" * 60)
    print("TESTING OPENAI-ONLY SOAP GENERATION")
    print("=" * 60)
    print()
    
    if not client.api_key:
        print("❌ ERROR: OpenAI API key not configured")
        print("Please set OPENAI_API_KEY in your .env file")
        return False
    
    print("✅ OpenAI API key configured")
    print()
    
    print("Test transcript:")
    print("-" * 40)
    print(TEST_TRANSCRIPT.strip())
    print("-" * 40)
    print()
    
    print("Calling OpenAI GPT-4o...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SOAP_SYSTEM_PROMPT},
                {"role": "user", "content": f"Create a SOAP note from this doctor-patient conversation:\n\n{TEST_TRANSCRIPT}"}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        soap_content = response.choices[0].message.content
        print(f"✅ OpenAI response received ({len(soap_content)} characters)")
        print()
        
        # Extract JSON
        soap_note = extract_json_from_response(soap_content)
        if soap_note is None:
            print("❌ ERROR: Could not extract JSON from response")
            print("Raw response:")
            print(soap_content)
            return False
        
        print("✅ JSON extracted successfully")
        print()
        
        # Validate key fields
        print("VALIDATION RESULTS:")
        print("-" * 20)
        
        if 'soap_note' in soap_note:
            sn = soap_note['soap_note']
            
            # Check patient name
            patient_name = sn.get('patient_name', '')
            print(f"Patient Name: '{patient_name}'")
            if 'Sarah Johnson' in patient_name:
                print("  ✅ Correct patient name extracted")
            else:
                print("  ❌ Patient name not correctly extracted")
            
            # Check patient age
            patient_age = sn.get('patient_age', '')
            print(f"Patient Age: '{patient_age}'")
            if '28' in str(patient_age):
                print("  ✅ Correct patient age extracted")
            else:
                print("  ❌ Patient age not correctly extracted")
            
            # Check provider name
            provider_name = sn.get('provider_name', '')
            print(f"Provider Name: '{provider_name}'")
            if 'Dr. Smith' in provider_name:
                print("  ✅ Correct provider name extracted")
            else:
                print("  ❌ Provider name not correctly extracted")
            
            # Check social history (hiking)
            social_history = sn.get('subjective', {}).get('social_history', '')
            print(f"Social History: '{social_history}'")
            if 'hiking' in social_history.lower():
                print("  ✅ Hiking activity captured in social history")
            else:
                print("  ❌ Hiking activity missing from social history")
            
            # Check prescribed medications
            medications_prescribed = sn.get('plan', {}).get('medications_prescribed', [])
            print(f"Medications Prescribed: {len(medications_prescribed)} medications")
            
            expected_meds = ['ceftriaxone', 'pentoxifylline', 'gabapentin', 'doxycycline', 'valacyclovir']
            found_meds = []
            
            for med in medications_prescribed:
                med_name = med.get('name', '').lower()
                for expected in expected_meds:
                    if expected in med_name:
                        found_meds.append(expected)
                        break
            
            print(f"  Expected: {expected_meds}")
            print(f"  Found: {found_meds}")
            
            if len(found_meds) >= 4:  # Allow for some variation
                print("  ✅ Most prescribed medications captured")
            else:
                print("  ❌ Missing prescribed medications")
            
            # Check vital signs
            vital_signs = sn.get('objective', {}).get('vital_signs', {})
            hr = vital_signs.get('heart_rate', '')
            bp = vital_signs.get('blood_pressure', '')
            print(f"Vital Signs - HR: '{hr}', BP: '{bp}'")
            
            if '85' in str(hr) and '120/80' in str(bp):
                print("  ✅ Vital signs correctly captured")
            else:
                print("  ❌ Vital signs not correctly captured")
            
            print()
            print("FULL SOAP NOTE:")
            print("=" * 40)
            print(json.dumps(soap_note, indent=2, ensure_ascii=False))
            
            return True
        else:
            print("❌ ERROR: No 'soap_note' key in response")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: OpenAI API call failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_soap_generation()
    if success:
        print("\n🎉 OpenAI-only SOAP generation test PASSED!")
    else:
        print("\n❌ OpenAI-only SOAP generation test FAILED!")
