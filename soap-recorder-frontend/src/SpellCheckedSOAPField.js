import React, { useState, useEffect, useRef } from 'react';
import MedicalSpellChecker from './MedicalSpellChecker';

const SpellCheckedSOAPField = ({ 
  value, 
  onChange, 
  isEditing = false,
  onEditModeChange,
  language = 'en',
  className = '',
  checkNow = false // explicit trigger from parent (SOAPRecorder)
}) => {
  const [localValue, setLocalValue] = useState(value || '');
  const [isLocalEditing, setIsLocalEditing] = useState(isEditing);
  const textAreaRef = useRef(null);

  useEffect(() => {
    setLocalValue(value || '');
  }, [value]);

  useEffect(() => {
    setIsLocalEditing(isEditing);
  }, [isEditing]);

  const handleTextChange = (newText) => {
    setLocalValue(newText);
    if (onChange) {
      onChange(newText);
    }
  };

  const handleSuggestionSelect = (newText, position) => {
    // When a suggestion is selected, enter edit mode and update text
    setLocalValue(newText);
    if (onChange) {
      onChange(newText);
    }
    setIsLocalEditing(true);
    
    // Notify parent component about edit mode change - pass metadata indicating this was a suggestion click
    if (onEditModeChange) {
      onEditModeChange(true, { triggeredBySuggestion: true });
    }
    
    // Focus and set cursor position after text is updated
    setTimeout(() => {
      if (textAreaRef.current) {
        textAreaRef.current.focus();
        textAreaRef.current.setSelectionRange(position.end, position.end);
      }
    }, 0);
  };

  const handleBlur = () => {
    // Delay to allow click events on suggestions to fire
    setTimeout(() => {
      setIsLocalEditing(false);
      if (onEditModeChange) {
        onEditModeChange(false);
      }
    }, 200);
  };

  if (isLocalEditing) {
    return (
      <textarea
        ref={textAreaRef}
        value={localValue}
        onChange={(e) => handleTextChange(e.target.value)}
        onBlur={handleBlur}
        className={`w-full p-2 border border-gray-300 rounded ${className}`}
        rows={3}
        dir={language === 'ar' ? 'rtl' : 'ltr'}
      />
    );
  }

  // Render medications: only underline drug name, not details (dosage, duration, frequency, route)
  const isMedicationsBlock = typeof localValue === 'string' && /medication|medications/i.test(localValue) === false;

  return (
    <div className={`spell-checked-field ${className}`}>
      <MedicalSpellChecker
        text={localValue}
        onTextChange={handleTextChange}
        onSuggestionSelect={handleSuggestionSelect}
        // If this field is a medications detail field (dosage/frequency/route strings),
        // disable spell-check to ensure ONLY medication names are underlined elsewhere.
        enabled={true}
        language={language}
        checkNow={checkNow}
      />
    </div>
  );
};

export default SpellCheckedSOAPField;
