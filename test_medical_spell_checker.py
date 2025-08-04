"""
Test script for medical spell checker functionality
"""

from medical_spell_check import MedicalSpellChecker

def test_medical_spell_checker():
    """Test the medical spell checker with sample text"""
    
    # Initialize spell checker
    checker = MedicalSpellChecker()
    
    # Test texts with intentional misspellings
    test_texts = [
        "Patient has diabetis and takes acitaminohen for pain relief.",
        "Diagnosed with pnuemonia, prescribed amoxicilin 500mg twice daily.",
        "History of hipertension, currently on lisinoprill.",
        "Complains of persistant cof and hedache for 3 days.",
        "Patient reports nausia and vomitting after eating."
    ]
    
    print("Medical Spell Checker Test")
    print("=" * 50)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        print("-" * 40)
        
        # Check the text
        results = checker.check_text(text)
        
        if not results:
            print("No medical terms found.")
            continue
        
        # Display results
        for result in results:
            term = result['term']
            is_correct = result['is_correct']
            suggestions = result['suggestions']
            confidence = result['confidence']
            
            status = "✓ Correct" if is_correct else "✗ Misspelled"
            print(f"\n  Term: '{term}' - {status} (Confidence: {confidence:.2f})")
            
            if not is_correct and suggestions:
                print(f"  Suggestions: {', '.join(suggestions[:3])}")
        
        # Show corrected text
        corrected = checker.correct_text(text, interactive=False)
        if corrected != text:
            print(f"\n  Corrected text: {corrected}")
    
    # Test contextual suggestions
    print("\n" + "=" * 50)
    print("Contextual Suggestion Test")
    print("-" * 40)
    
    context = "Patient was prescribed acitaminohen 500mg for pain management."
    term = "acitaminohen"
    position = context.find(term)
    
    suggestions = checker.get_contextual_suggestions(term, context, position)
    print(f"Context: {context}")
    print(f"Term: '{term}'")
    print(f"Contextual suggestions: {', '.join(suggestions[:3])}")

def test_medical_patterns():
    """Test medical term pattern matching"""
    
    checker = MedicalSpellChecker()
    
    test_text = """
    Patient presents with acute bronchitis and hypertension. 
    Current medications include metformin 500mg, lisinopril 10mg daily.
    Physical exam reveals BP 140/90, HR 72, O2 sat 98%.
    Plan: Start amoxicillin, follow-up in 2 weeks for echocardiogram.
    """
    
    print("\n" + "=" * 50)
    print("Medical Pattern Recognition Test")
    print("-" * 40)
    print(f"Test text:\n{test_text}")
    
    terms = checker.identify_medical_terms(test_text)
    
    print(f"\nIdentified {len(terms)} medical terms:")
    for term, start, end in terms:
        print(f"  - '{term}' (position {start}-{end})")

if __name__ == "__main__":
    test_medical_spell_checker()
    test_medical_patterns()
    
    print("\n✅ Medical spell checker tests completed!")
