import React, { useState, useEffect, useRef } from 'react';
import MedicalSpellChecker from './MedicalSpellChecker';

const SpellCheckedSOAPField = ({ 
  value, 
  onChange, 
  isEditing = false,
  onEditModeChange,
  language = 'en',
  className = '',
  checkNow = false, // explicit trigger from parent (SOAPRecorder)
  checkVersion = 0   // numeric trigger to force a check every click
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

  const handleSuggestionSelect = (newText /* , position */) => {
    // Live update without forcing edit mode or a full re-check.
    setLocalValue(newText);
    if (onChange) {
      onChange(newText);
    }
    // Do NOT enter edit mode; keep current UI state
    // Do NOT focus or move cursor; MedicalSpellChecker will locally restyle the corrected token
    // Do NOT trigger onEditModeChange; this is an inline correction
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

  return (
    <div className={`spell-checked-field ${className}`}>
      <MedicalSpellChecker
        text={localValue}
        onTextChange={handleTextChange}
        onSuggestionSelect={handleSuggestionSelect}
        enabled={true}
        language={language}
        checkNow={checkNow}
        checkVersion={checkVersion}
      />
    </div>
  );
};

export default SpellCheckedSOAPField;
