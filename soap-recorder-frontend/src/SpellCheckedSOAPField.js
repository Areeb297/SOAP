import React, { useState, useEffect } from 'react';
import MedicalSpellChecker from './MedicalSpellChecker';

const SpellCheckedSOAPField = ({ 
  value, 
  onChange, 
  isEditing = false,
  language = 'en',
  className = ''
}) => {
  const [localValue, setLocalValue] = useState(value || '');

  useEffect(() => {
    setLocalValue(value || '');
  }, [value]);

  const handleTextChange = (newText) => {
    setLocalValue(newText);
    if (onChange) {
      onChange(newText);
    }
  };

  if (isEditing) {
    return (
      <textarea
        value={localValue}
        onChange={(e) => handleTextChange(e.target.value)}
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
        enabled={true}
        language={language}
      />
    </div>
  );
};

export default SpellCheckedSOAPField;
