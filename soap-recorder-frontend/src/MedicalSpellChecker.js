import React, { useEffect, useState, useRef, useCallback } from 'react';
import './MedicalSpellChecker.css';

const MedicalSpellChecker = ({ text, onTextChange, enabled = true }) => {
  const [medicalTerms, setMedicalTerms] = useState([]);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionPosition, setSuggestionPosition] = useState({ top: 0, left: 0 });
  const [isChecking, setIsChecking] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [nlpStatus, setNlpStatus] = useState(null);
  
  // Client-side caching
  const [termCache, setTermCache] = useState(new Map());
  const [cacheStats, setCacheStats] = useState({ hits: 0, misses: 0 });
  const textAreaRef = useRef(null);
  const suggestionsRef = useRef(null);
  const checkTimeoutRef = useRef(null);
  
  // Dynamic backend URL
  const BACKEND_URL =
    process.env.REACT_APP_BACKEND_URL ||
    (window.location.hostname === 'localhost'
      ? 'http://localhost:5001'
      : 'https://soap-598q.onrender.com');

  // Fetch NLP status on component mount
  useEffect(() => {
    const fetchNlpStatus = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/medical-nlp-status`);
        if (response.ok) {
          const status = await response.json();
          setNlpStatus(status);
        }
      } catch (error) {
        console.error('Error fetching NLP status:', error);
      }
    };
    
    fetchNlpStatus();
  }, [BACKEND_URL]);

  // Check medical terms with debouncing and caching
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

    // Create cache key based on text content
    const cacheKey = textToCheck.trim().toLowerCase();
    
    // Check cache first
    if (termCache.has(cacheKey)) {
      const cachedResult = termCache.get(cacheKey);
      setMedicalTerms(cachedResult);
      setCacheStats(prev => ({ ...prev, hits: prev.hits + 1 }));
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
        const results = data.results || [];
        
        // Cache the results
        setTermCache(prev => {
          const newCache = new Map(prev);
          newCache.set(cacheKey, results);
          
          // Limit cache size to prevent memory issues
          if (newCache.size > 100) {
            const firstKey = newCache.keys().next().value;
            newCache.delete(firstKey);
          }
          
          return newCache;
        });
        
        setCacheStats(prev => ({ ...prev, misses: prev.misses + 1 }));
        setMedicalTerms(results);
      }
    } catch (error) {
      console.error('Error checking medical terms:', error);
    } finally {
      setIsChecking(false);
    }
  }, [enabled, BACKEND_URL, termCache]);

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
      const { start, end } = selectedTerm;
      
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

  // Get CSS class based on term category and correctness
  const getTermClassName = (term) => {
    const baseClass = term.isCorrect ? 'medical-term-correct' : 'medical-term-incorrect';
    const category = term.category || 'general';
    
    // Add category-specific classes
    const categoryClass = `medical-category-${category.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`;
    
    return `${baseClass} ${categoryClass}`;
  };

  // Get term title/tooltip based on category
  const getTermTitle = (term) => {
    const category = term.category || 'medical term';
    const action = term.isCorrect ? 'Click to confirm this' : 'Click for spelling suggestions for this';
    return `${action} ${category.replace(/_/g, ' ')}`;
  };

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

      // Add the highlighted term with category-based styling
      const className = getTermClassName(term);
      const title = getTermTitle(term);

      elements.push(
        <span
          key={`term-${index}`}
          className={className}
          onClick={(e) => handleTermClick(term, e)}
          title={title}
          data-category={term.category || 'general'}
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

  // Render legend
  const renderLegend = () => {
    if (!showLegend || medicalTerms.length === 0) return null;

    // Get unique categories from current terms
    const categories = [...new Set(medicalTerms.map(term => term.category || 'general'))];
    
    return (
      <div className="medical-legend">
        <div className="legend-header">
          <span>Medical Term Legend</span>
          <button 
            className="legend-close"
            onClick={() => setShowLegend(false)}
            aria-label="Close legend"
          >
            ×
          </button>
        </div>
        <div className="legend-content">
          <div className="legend-section">
            <h4>By Status:</h4>
            <div className="legend-item">
              <span className="legend-color medical-term-correct"></span>
              <span>Correct Medical Terms (Blue)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color medical-term-incorrect"></span>
              <span>Spelling Errors (Red)</span>
            </div>
          </div>
          
          {categories.length > 1 && (
            <div className="legend-section">
              <h4>By Category:</h4>
              {categories.map(category => (
                <div key={category} className="legend-item">
                  <span className={`legend-color medical-category-${category.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`}></span>
                  <span>{category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                </div>
              ))}
            </div>
          )}
          
          {nlpStatus && (
            <div className="legend-section">
              <h4>NLP Status:</h4>
              <div className="nlp-status">
                <span className={`status-indicator ${nlpStatus.available ? 'available' : 'unavailable'}`}></span>
                <span>{nlpStatus.available ? 'Medical NLP Active' : 'Basic Mode'}</span>
                {nlpStatus.models?.nlp && (
                  <div className="model-info">Using: {nlpStatus.models.nlp}</div>
                )}
              </div>
            </div>
          )}
          
          <div className="legend-section">
            <h4>Performance:</h4>
            <div className="cache-stats">
              <div className="cache-stat">
                <span>Cache Size: {termCache.size}</span>
              </div>
              <div className="cache-stat">
                <span>Cache Hits: {cacheStats.hits}</span>
              </div>
              <div className="cache-stat">
                <span>API Calls: {cacheStats.misses}</span>
              </div>
              {(cacheStats.hits + cacheStats.misses) > 0 && (
                <div className="cache-stat">
                  <span>Hit Rate: {Math.round((cacheStats.hits / (cacheStats.hits + cacheStats.misses)) * 100)}%</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="medical-spell-checker" ref={textAreaRef}>
      {isChecking && (
        <div className="spell-check-indicator">
          Checking spelling...
        </div>
      )}
      
      {renderLegend()}
      
      <div className="spell-check-content">
        {medicalTerms.length > 0 && (
          <div className="spell-checker-controls">
            <button 
              className="legend-toggle"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowLegend(!showLegend);
              }}
              title="Show/hide legend"
            >
              {showLegend ? 'Hide' : 'Show'} Legend
            </button>
            <span className="term-count">
              {medicalTerms.length} medical term{medicalTerms.length !== 1 ? 's' : ''} found
            </span>
          </div>
        )}
        
        {renderHighlightedText()}
      </div>
      
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
