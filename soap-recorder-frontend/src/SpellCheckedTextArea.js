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
  rows = 4,
  checkNow = false, // explicit trigger from parent
  checkVersion = 0 // numeric trigger to force a check every click
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
    // Task [6]: Replace in-place silently without reopening the editor or forcing a re-check
    setLocalValue(newText);
    onChange(newText);
    // Do NOT set isEditing(true); stay in view mode to avoid reopening the full editor
    // Do NOT refocus textarea or change selection here
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
              checkNow={checkNow}
              checkVersion={checkVersion}
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
