import re

def test_english_extraction():
    # Test English patient name extraction
    test_transcripts = [
        "Dr. Emily Chen: Good morning. Patient: Robert Smith, 52 years old.",
        "Dr. Emily Chen here. The patient is Robert Smith, a 52-year-old male.",
        "This is Robert Smith, he's 52 years old.",
        "Patient is Dr. Johnson, age 52",  # Should keep Dr. if patient is a doctor
        "My name is Robert Smith and I'm 52 years old.",
    ]
    
    for transcript in test_transcripts:
        print(f"\nTesting: {transcript}")
        
        # Extract patient name
        patient_patterns = [
            r"patient(?:\s+is)?[:\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+is\s+(?:a\s+)?\d+\s*(?:-)?\s*year",
            r"I'm\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"My name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"This is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        ]
        
        patient_name = "Unknown"
        for pattern in patient_patterns:
            match = re.search(pattern, transcript)
            if match:
                extracted_name = match.group(1)
                # Validate it's a reasonable name
                if len(extracted_name) > 2 and extracted_name.lower() not in ['the', 'and', 'with', 'this', 'that']:
                    patient_name = extracted_name
                    print(f"  Found patient: {patient_name} (pattern: {pattern})")
                    break
        
        if patient_name == "Unknown":
            print("  No patient name found")

def test_arabic_extraction():
    # Test Arabic patient name extraction
    test_transcripts = [
        "د. إيميلي تشين: صباح الخير. المريض: روبرت سميث، 52 سنة.",
        "المريضة ليلى أحمد، عمرها 52 سنة",
        "اسمي ليلى أحمد وعمري 52 سنة",
        "هذا المريض اسمه أحمد علي",
    ]
    
    for transcript in test_transcripts:
        print(f"\nTesting: {transcript}")
        
        # Extract patient name
        name_patterns = [
            r"المريض\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"المريضة\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسمي\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسمه\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسمها\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
        ]
        
        patient_name = "غير محدد"
        for pattern in name_patterns:
            match = re.search(pattern, transcript)
            if match:
                extracted_name = match.group(1)
                if len(extracted_name) > 2:
                    patient_name = extracted_name
                    print(f"  Found patient: {patient_name} (pattern: {pattern})")
                    break
        
        if patient_name == "غير محدد":
            print("  No patient name found")

if __name__ == "__main__":
    print("Testing English name extraction:")
    test_english_extraction()
    print("\n\nTesting Arabic name extraction:")
    test_arabic_extraction()
