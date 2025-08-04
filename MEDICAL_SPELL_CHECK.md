# Medical Spell Check Feature

## Overview
The SOAP Note Generator now includes an intelligent medical term spell correction and validation system that operates seamlessly across both the transcript generation phase and the final SOAP note generation.

## Features

### 1. Automatic Detection & Highlighting
- **Red Underlines (Misspelled Terms)**: Automatically identifies and highlights misspelled medical terms with a red underline
- **Blue Underlines (Correctly Spelled Terms)**: Highlights correctly spelled medical terms with a blue underline for confirmation

### 2. Interactive Corrections
- Click on any underlined term to see suggestions
- For misspelled terms: Get a prioritized list of correct spelling suggestions
- For correct terms: Confirm the term or view alternatives if uncertain

### 3. Real-time Processing
- Spell checking happens automatically as you type or after transcription
- No manual "check spelling" action required
- Debounced checking to maintain performance

### 4. Medical Context Awareness
- Uses a comprehensive medical dictionary with common terms, medications, symptoms, and conditions
- Integrates with SNOMED CT API for validation
- Considers context when suggesting corrections

## Technical Implementation

### Backend Components

1. **Medical Dictionary** (`medical_spell_check/medical_dictionary.py`)
   - Contains common medical terms and their misspellings
   - Supports custom term addition
   - Provides fuzzy matching capabilities

2. **SNOMED API Integration** (`medical_spell_check/snomed_api.py`)
   - Validates terms against SNOMED CT database
   - Provides professional medical term suggestions
   - Handles medication-specific searches

3. **Spell Checker** (`medical_spell_check/spell_checker.py`)
   - Main spell checking logic
   - Identifies medical terms using patterns and dictionary
   - Provides contextual suggestions

### Frontend Components

1. **MedicalSpellChecker** (`src/MedicalSpellChecker.js`)
   - React component for displaying spell-checked text
   - Handles term highlighting and suggestion display

2. **SpellCheckedTextArea** (`src/SpellCheckedTextArea.js`)
   - Wrapper component for editable text with spell checking
   - Manages edit/view modes

3. **SpellCheckedSOAPField** (`src/SpellCheckedSOAPField.js`)
   - Specialized component for SOAP note fields
   - Handles both short and long text fields

## API Endpoints

### `/check-medical-terms` (POST)
Check medical terms in a text block
```json
Request:
{
  "text": "Patient has diabetis and takes acitaminohen"
}

Response:
{
  "results": [
    {
      "term": "diabetis",
      "start": 12,
      "end": 20,
      "isCorrect": false,
      "suggestions": ["diabetes"],
      "confidence": 0.9
    }
  ]
}
```

### `/validate-medical-term` (POST)
Validate a single medical term
```json
Request:
{
  "term": "acitaminohen",
  "context": "takes acitaminohen for pain",
  "position": 6
}

Response:
{
  "term": "acitaminohen",
  "isCorrect": false,
  "suggestions": ["acetaminophen"],
  "confidence": 0.95
}
```

## Configuration

### Adding Custom Medical Terms
You can add custom medical terms to the dictionary:

```python
from medical_spell_check import MedicalDictionary

med_dict = MedicalDictionary()
med_dict.add_custom_term("custom_drug", ["custm_drug", "custom_drg"])
med_dict.export_dictionary("custom_terms.json")
```

### Language Support
- Supports both English and Arabic medical terms
- Automatically adjusts text direction for Arabic content

## Performance Considerations

1. **Debouncing**: Spell checking is debounced by 500ms to avoid excessive API calls
2. **Caching**: Common terms are cached locally for faster lookup
3. **Batch Processing**: Multiple terms are checked in a single request when possible

## Troubleshooting

### TextBlob Setup
If you encounter TextBlob errors, run:
```bash
python setup_textblob.py
```

### SNOMED API Issues
- The system uses the public SNOMED CT API
- If the API is unavailable, the system falls back to local dictionary
- No authentication required for basic searches

## Future Enhancements

1. **Machine Learning Integration**: Train custom models on medical transcripts
2. **Specialty-Specific Dictionaries**: Add specialized terms for different medical fields
3. **Abbreviation Expansion**: Automatically expand common medical abbreviations
4. **Multi-language Support**: Extend beyond English and Arabic
5. **Offline Mode**: Enhanced offline capabilities with larger local dictionary
