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
        <div 
          className="spell-check-container"
          onClick={!disabled ? handleEditClick : undefined}
          title={!disabled ? "Click to edit" : ""}
        >
          {localValue ? (
            <MedicalSpellChecker
              text={localValue}
              onTextChange={handleSpellCheckerChange}
              enabled={enableSpellCheck && !disabled}
              language={language}
            />
          ) : (
            <div className="placeholder-text">{placeholder}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default SpellCheckedTextArea;
