import React, { useState, useRef, useEffect } from 'react';
import MedicalSpellChecker from './MedicalSpellChecker';
import './SpellCheckedTextArea.css';

const SpellCheckedTextArea = ({ 
  value, 
  onChange, 
  placeholder = 'Enter text...', 
  className = '',
  disabled = false,
  language = 'en',
  enableSpellCheck = true,
  rows = 4
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [localValue, setLocalValue] = useState(value);
  const textAreaRef = useRef(null);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleEditClick = () => {
    setIsEditing(true);
    setTimeout(() => {
      if (textAreaRef.current) {
        textAreaRef.current.focus();
        textAreaRef.current.setSelectionRange(localValue.length, localValue.length);
      }
    }, 0);
  };

  const handleBlur = () => {
    // Delay to allow click events on suggestions to fire
    setTimeout(() => {
      setIsEditing(false);
    }, 200);
  };

  const handleChange = (e) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    onChange(newValue);
  };

  const handleSpellCheckerChange = (newText) => {
    setLocalValue(newText);
    onChange(newText);
  };

  const handleSuggestionSelect = (newText, position) => {
    // When a suggestion is selected, enter edit mode and update text
    setLocalValue(newText);
    onChange(newText);
    setIsEditing(true);
    
    // Focus and set cursor position after text is updated
    setTimeout(() => {
      if (textAreaRef.current) {
        textAreaRef.current.focus();
        textAreaRef.current.setSelectionRange(position.end, position.end);
      }
    }, 0);
  };

  return (
    <div className={`spell-checked-textarea ${className} ${disabled ? 'disabled' : ''}`}>
      {isEditing ? (
        <textarea
          ref={textAreaRef}
          value={localValue}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder={placeholder}
          disabled={disabled}
          rows={rows}
          className="edit-textarea"
          dir={language === 'ar' ? 'rtl' : 'ltr'}
        />
      ) : (
        <div className="spell-check-container">
          {/* Edit button */}
          {!disabled && (
            <button
              className="edit-transcript-button"
              onClick={handleEditClick}
              title="Edit transcript"
            >
              ✏️ Edit
            </button>
          )}
          
          {localValue ? (
            <MedicalSpellChecker
              text={localValue}
              onTextChange={handleSpellCheckerChange}
              onSuggestionSelect={handleSuggestionSelect}
              enabled={enableSpellCheck && !disabled}
              language={language}
            />
          ) : (
            <div className="placeholder-text" onClick={!disabled ? handleEditClick : undefined}>
              {placeholder}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SpellCheckedTextArea;
