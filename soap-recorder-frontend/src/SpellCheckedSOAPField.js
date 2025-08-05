import React, { useState, useEffect, useRef } from 'react';
import MedicalSpellChecker from './MedicalSpellChecker';

const SpellCheckedSOAPField = ({ 
  value, 
  onChange, 
  isEditing = false,
  onEditModeChange,
  language = 'en',
  className = ''
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
    
    // Notify parent component about edit mode change
    if (onEditModeChange) {
      onEditModeChange(true);
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

  return (
    <div className={`spell-checked-field ${className}`}>
      <MedicalSpellChecker
        text={localValue}
        onTextChange={handleTextChange}
        onSuggestionSelect={handleSuggestionSelect}
        enabled={true}
        language={language}
      />
    </div>
  );
};

export default SpellCheckedSOAPField;
