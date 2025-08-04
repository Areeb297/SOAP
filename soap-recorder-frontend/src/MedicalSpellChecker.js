import React, { useEffect, useState, useRef, useCallback } from 'react';
import './MedicalSpellChecker.css';

const MedicalSpellChecker = ({ text, onTextChange, enabled = true, language = 'en' }) => {
  const [medicalTerms, setMedicalTerms] = useState([]);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionPosition, setSuggestionPosition] = useState({ top: 0, left: 0 });
  const [isChecking, setIsChecking] = useState(false);
  const textAreaRef = useRef(null);
  const suggestionsRef = useRef(null);
  const checkTimeoutRef = useRef(null);
  
  // Dynamic backend URL
  const BACKEND_URL =
    process.env.REACT_APP_BACKEND_URL ||
    (window.location.hostname === 'localhost'
      ? 'http://localhost:5001'
      : 'https://soap-598q.onrender.com');

  // Check medical terms with debouncing
  const checkMedicalTerms = useCallback(async (textToCheck) => {
    if (!enabled || !textToCheck) {
      setMedicalTerms([]);
      return;
    }

    // Fix .trim() error by ensuring textToCheck is a string
    if (typeof textToCheck !== 'string') {
      textToCheck = String(textToCheck || '');
    }

    if (!textToCheck.trim()) {
      setMedicalTerms([]);
      return;
    }

    setIsChecking(true);
    try {
      const response = await fetch(`${BACKEND_URL}/check-medical-terms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: textToCheck }),
      });

      if (response.ok) {
        const data = await response.json();
        setMedicalTerms(data.results || []);
      }
    } catch (error) {
      console.error('Error checking medical terms:', error);
    } finally {
      setIsChecking(false);
    }
  }, [enabled, BACKEND_URL]);

  // Debounced text checking
  useEffect(() => {
    if (checkTimeoutRef.current) {
      clearTimeout(checkTimeoutRef.current);
    }

    checkTimeoutRef.current = setTimeout(() => {
      checkMedicalTerms(text);
    }, 500); // Wait 500ms after user stops typing

    return () => {
      if (checkTimeoutRef.current) {
        clearTimeout(checkTimeoutRef.current);
      }
    };
  }, [text, checkMedicalTerms]);

  // Handle term click
  const handleTermClick = async (term, event) => {
    event.preventDefault();
    event.stopPropagation();

    const rect = event.target.getBoundingClientRect();
    const containerRect = textAreaRef.current.parentElement.getBoundingClientRect();

    // Calculate position relative to the container
    setSuggestionPosition({
      top: rect.bottom - containerRect.top + 5,
      left: rect.left - containerRect.left,
    });

    setSelectedTerm(term);
    setSuggestions(term.suggestions || []);
    setShowSuggestions(true);
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion) => {
    if (selectedTerm && onTextChange) {
      // Replace the term in the text
      let newText = text;
      const { start, end, term } = selectedTerm;
      
      // Calculate the actual positions in the current text
      const beforeText = text.substring(0, start);
      const afterText = text.substring(end);
      
      newText = beforeText + suggestion + afterText;
      onTextChange(newText);
    }

    setShowSuggestions(false);
    setSelectedTerm(null);
  };

  // Handle confirmation for correct terms
  const handleConfirmTerm = async (confirmed) => {
    if (selectedTerm && confirmed) {
      // Add the term to the dynamic medicine list
      try {
        await fetch(`${BACKEND_URL}/add-medicine`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ term: selectedTerm.term }),
        });
      } catch (error) {
        console.error('Error adding medicine to dynamic list:', error);
      }
    }
    setShowSuggestions(false);
    setSelectedTerm(null);
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Render text with highlighted medical terms
  const renderHighlightedText = () => {
    if (!enabled || medicalTerms.length === 0) {
      return <div className="spell-check-text">{text}</div>;
    }

    // Ensure text is a string
    const textStr = typeof text === 'string' ? text : String(text || '');
    
    let lastIndex = 0;
    const elements = [];

    // Sort medical terms by position and remove duplicates
    const sortedTerms = [...medicalTerms]
      .sort((a, b) => a.start - b.start)
      .filter((term, index, array) => {
        // Remove duplicates based on position and term
        return index === 0 || 
               term.start !== array[index - 1].start || 
               term.term !== array[index - 1].term;
      });

    sortedTerms.forEach((term, index) => {
      // Add text before the term
      if (term.start > lastIndex) {
        elements.push(
          <span key={`text-${index}`}>
            {textStr.substring(lastIndex, term.start)}
          </span>
        );
      }

      // Add the highlighted term
      const className = term.isCorrect 
        ? 'medical-term-correct' 
        : 'medical-term-incorrect';

      elements.push(
        <span
          key={`term-${index}`}
          className={className}
          onClick={(e) => handleTermClick(term, e)}
          title={term.isCorrect ? 'Click to confirm this medical term' : 'Click for spelling suggestions'}
        >
          {textStr.substring(term.start, term.end)}
        </span>
      );

      lastIndex = term.end;
    });

    // Add remaining text
    if (lastIndex < textStr.length) {
      elements.push(
        <span key="text-final">
          {textStr.substring(lastIndex)}
        </span>
      );
    }

    return <div className="spell-check-text">{elements}</div>;
  };

  return (
    <div className="medical-spell-checker" ref={textAreaRef}>
      {isChecking && (
        <div className="spell-check-indicator">
          Checking spelling...
        </div>
      )}
      
      {renderHighlightedText()}
      
      {showSuggestions && suggestions.length > 0 && (
        <div 
          ref={suggestionsRef}
          className="suggestions-dropdown"
          style={{
            position: 'absolute',
            top: `${suggestionPosition.top}px`,
            left: `${suggestionPosition.left}px`,
          }}
        >
          <div className="suggestions-header">
            {selectedTerm.isCorrect ? 'Confirm Medical Term' : 'Spelling Suggestions'}
          </div>
          <div className="suggestions-list">
            {selectedTerm.isCorrect ? (
              <div className="suggestion-item confirm-item">
                <div>Are you sure this is the correct medical term?</div>
                <div className="confirm-buttons">
                  <button 
                    className="confirm-yes"
                    onClick={() => handleConfirmTerm(true)}
                  >
                    Yes
                  </button>
                  <button 
                    className="confirm-no"
                    onClick={() => {
                      // Show alternative suggestions
                      setSuggestions(['Loading suggestions...']);
                      // Fetch alternative suggestions
                      fetch(`${BACKEND_URL}/validate-medical-term`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          term: selectedTerm.term,
                          context: text,
                          position: selectedTerm.start
                        })
                      })
                      .then(res => res.json())
                      .then(data => {
                        setSuggestions(data.suggestions || []);
                      });
                    }}
                  >
                    No, show alternatives
                  </button>
                </div>
              </div>
            ) : (
              suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="suggestion-item"
                  onClick={() => handleSuggestionSelect(suggestion)}
                >
                  {suggestion}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MedicalSpellChecker;
