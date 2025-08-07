import React, { useEffect, useState, useRef, useCallback } from 'react';
import './MedicalSpellChecker.css';

const MedicalSpellChecker = ({ text, onTextChange, enabled = true, onSuggestionSelect, checkNow = false }) => {
  const [medicalTerms, setMedicalTerms] = useState([]);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionPosition, setSuggestionPosition] = useState({ top: 0, left: 0 });
  const [isChecking, setIsChecking] = useState(false);
  const [showingAlternatives, setShowingAlternatives] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [nlpStatus, setNlpStatus] = useState(null);
  
  // Client-side caching
  const [termCache, setTermCache] = useState(new Map());
  const [cacheStats, setCacheStats] = useState({ hits: 0, misses: 0 });
  const textAreaRef = useRef(null);
  const suggestionsRef = useRef(null);
  const checkTimeoutRef = useRef(null);
  const [lastCheckedKey, setLastCheckedKey] = useState(null);
  
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

  // State for unique term counts
  const [uniqueTermCount, setUniqueTermCount] = useState(0);
  const [totalOccurrences, setTotalOccurrences] = useState(0);

  // Explicit spell-check only when invoked (no auto/debounce)
  const checkMedicalTerms = useCallback(async (textToCheck) => {
    if (!enabled) return;

    const normalized = typeof textToCheck === 'string' ? textToCheck : String(textToCheck || '');
    const trimmed = normalized.trim();
    if (!trimmed) {
      setMedicalTerms([]);
      setUniqueTermCount(0);
      setTotalOccurrences(0);
      return;
    }

    const cacheKey = trimmed.toLowerCase();

    // Do not re-check the exact same content unless checkNow toggles again
    if (lastCheckedKey === cacheKey && (medicalTerms?.length ?? 0) > 0) {
      return;
    }

    // Serve from cache
    if (termCache.has(cacheKey)) {
      const cachedResult = termCache.get(cacheKey);
      setMedicalTerms(cachedResult.results || cachedResult);
      setUniqueTermCount(cachedResult.unique_count || 0);
      setTotalOccurrences(cachedResult.total_occurrences || (cachedResult.results || cachedResult).length);
      setCacheStats(prev => ({ ...prev, hits: prev.hits + 1 }));
      setLastCheckedKey(cacheKey);
      return;
    }

    setIsChecking(true);
    try {
      const response = await fetch(`${BACKEND_URL}/check-medical-terms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: normalized }),
      });

      if (response.ok) {
        const data = await response.json();
        const results = data.results || [];
        const uniqueCount = data.unique_count || 0;
        const totalOccurs = data.total_occurrences || results.length;

        setTermCache(prev => {
          const newCache = new Map(prev);
          newCache.set(cacheKey, data);
          if (newCache.size > 100) {
            const firstKey = newCache.keys().next().value;
            newCache.delete(firstKey);
          }
          return newCache;
        });

        setCacheStats(prev => ({ ...prev, misses: prev.misses + 1 }));
        setMedicalTerms(results);
        setUniqueTermCount(uniqueCount);
        setTotalOccurrences(totalOccurs);
        setLastCheckedKey(cacheKey);
      }
    } catch (error) {
      console.error('Error checking medical terms:', error);
    } finally {
      setIsChecking(false);
    }
  }, [enabled, BACKEND_URL, termCache, lastCheckedKey, medicalTerms]);

  // Explicit trigger: run only when parent toggles checkNow
  useEffect(() => {
    if (!enabled) return;
    if (checkNow) {
      // Ensure no pending timers execute
      if (checkTimeoutRef.current) {
        clearTimeout(checkTimeoutRef.current);
        checkTimeoutRef.current = null;
      }
      checkMedicalTerms(text);
    }
  }, [checkNow, enabled, text, checkMedicalTerms]);

  // Handle term click
  const handleTermClick = async (term, event) => {
    event.preventDefault();
    event.stopPropagation();
    
    console.log('Medical term clicked, preventing edit mode trigger');

    const rect = event.target.getBoundingClientRect();
    const containerRect = textAreaRef.current.parentElement.getBoundingClientRect();

    // Calculate position relative to the container
    setSuggestionPosition({
      top: rect.bottom - containerRect.top + 5,
      left: rect.left - containerRect.left,
    });

    setSelectedTerm(term);
    setShowingAlternatives(false); // Reset alternatives state for new term
    
    // Combine spell-check suggestions with database suggestions
    let allSuggestions = term.suggestions || [];
    
    // Fetch database suggestions
    try {
      console.log(`Fetching database suggestions for term: "${term.term}"`);
      const response = await fetch(`${BACKEND_URL}/suggest?word=${encodeURIComponent(term.term)}`);
      console.log(`Database response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Database response data:', data);
        
        const dbSuggestions = data.results || [];
        console.log(`Database suggestions found: ${dbSuggestions.length}`);
        console.log('Database suggestions:', dbSuggestions);
        
        // Add database suggestions with source information
        const formattedDbSuggestions = dbSuggestions.map(result => ({
          value: result.value,
          typeName: result.typeName,
          source: 'database'
        }));
        
        console.log('Formatted database suggestions:', formattedDbSuggestions);
        
        // Combine suggestions: spell-check first, then database
        allSuggestions = [
          ...allSuggestions.map(s => ({ value: s, source: 'spellcheck' })),
          ...formattedDbSuggestions
        ];
        
        console.log('All combined suggestions:', allSuggestions);
      } else {
        console.error(`Database request failed with status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error fetching database suggestions:', error);
      // Continue with just spell-check suggestions if database fails
      allSuggestions = allSuggestions.map(s => ({ value: s, source: 'spellcheck' }));
    }
    
    console.log('Setting suggestions state:', allSuggestions);
    console.log('Current showSuggestions state before:', showSuggestions);
    setSuggestions(allSuggestions);
    setShowSuggestions(true);
    console.log('Set showSuggestions to true');
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion) => {
    if (selectedTerm) {
      const { start, end } = selectedTerm;

      // Calculate the actual positions in the current text
      const beforeText = text.substring(0, start);
      const afterText = text.substring(end);

      // Extract the actual value from suggestion object or use as string
      const replacementText = typeof suggestion === 'object' ? suggestion.value : suggestion;

      const newText = beforeText + replacementText + afterText;

      // Replace text upstream (STRICT: no auto re-check, no auto re-highlight)
      if (onSuggestionSelect) {
        onSuggestionSelect(newText, { start, end: start + replacementText.length });
      } else if (onTextChange) {
        onTextChange(newText);
      }

      // Immediately clear ALL highlights to ensure plain black text until user triggers spell-check.
      setMedicalTerms([]);

      // Also reset cache key marker so future explicit checks are allowed on same content
      setLastCheckedKey(null);
    }

    // Close UI and reset state
    setShowSuggestions(false);
    setSelectedTerm(null);
    setShowingAlternatives(false); // Reset alternatives state
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
    setShowingAlternatives(false); // Reset alternatives state
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowSuggestions(false);
        setShowingAlternatives(false); // Reset alternatives state
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Get CSS class based on term category and correctness
  const getTermClassName = (term) => {
    // Normalize backend fields (snake_case and camelCase)
    const isCorrect = term.is_correct ?? term.isCorrect ?? false;
    const needsCorrection = term.needs_correction ?? term.needsCorrection ?? false;
    const source = (term.source || '').toString().toLowerCase();

    // Treat any "needs_correction" term as incorrect (red underline)
    // Otherwise, consider correct only if explicitly validated
    const validatedSources = new Set([
      'dynamic_list',
      'local_dictionary',
      'snomed_ct',
      'llm_identified_snomed_timeout',
      'llm_corrected'
    ]);
    const isValidated = Boolean(isCorrect) || validatedSources.has(source);

    const baseClass =
      needsCorrection || !isValidated
        ? 'medical-term-incorrect' // red underline
        : 'medical-term-correct';  // blue underline

    const category = term.category || 'general';
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

  // Debug logging for render
  console.log('MedicalSpellChecker render - showSuggestions:', showSuggestions, 'suggestions:', suggestions, 'selectedTerm:', selectedTerm, 'showingAlternatives:', showingAlternatives);

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
              {uniqueTermCount > 0 ? uniqueTermCount : medicalTerms.length} medical term{(uniqueTermCount > 0 ? uniqueTermCount : medicalTerms.length) !== 1 ? 's' : ''} found
              {totalOccurrences > uniqueTermCount && uniqueTermCount > 0 && (
                <span className="occurrence-count"> ({totalOccurrences} occurrences)</span>
              )}
            </span>
          </div>
        )}
        
        {renderHighlightedText()}
      </div>
      
      {(() => {
        console.log('Rendering check - showSuggestions:', showSuggestions, 'suggestions.length:', suggestions.length, 'suggestions:', suggestions);
        const shouldShow = showSuggestions && (suggestions.length > 0 || selectedTerm);
        console.log('Should show dropdown:', shouldShow);
        return shouldShow;
      })() && (
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
            {selectedTerm.isCorrect && !showingAlternatives ? 'Confirm Medical Term' : 'Spelling Suggestions'}
          </div>
          <div className="suggestions-list">
            {selectedTerm.isCorrect && !showingAlternatives ? (
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
                    onClick={async (event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      console.log('User clicked "No, show alternatives"');
                      setShowingAlternatives(true); // Set state to show alternatives
                      setSuggestions([{ value: 'Loading suggestions...', source: 'loading' }]);
                      
                      // Fetch database suggestions using same logic as handleTermClick
                      let allSuggestions = [];
                      
                      try {
                        console.log(`Fetching alternatives for term: "${selectedTerm.term}"`);
                        const response = await fetch(`${BACKEND_URL}/suggest?word=${encodeURIComponent(selectedTerm.term)}`);
                        console.log(`Alternative suggestions response status: ${response.status}`);
                        
                        if (response.ok) {
                          const data = await response.json();
                          console.log('Alternative suggestions data:', data);
                          
                          const dbSuggestions = data.results || [];
                          console.log(`Alternative database suggestions found: ${dbSuggestions.length}`);
                          
                          // Format database suggestions
                          allSuggestions = dbSuggestions.map(result => ({
                            value: result.value,
                            typeName: result.typeName,
                            source: 'database'
                          }));
                          
                          console.log('Formatted alternative suggestions:', allSuggestions);
                          console.log('About to set alternative suggestions state');
                        } else {
                          console.error(`Alternative suggestions request failed: ${response.status}`);
                          allSuggestions = [{ value: 'No alternatives found', source: 'error' }];
                        }
                      } catch (error) {
                        console.error('Error fetching alternative suggestions:', error);
                        allSuggestions = [{ value: 'Error loading alternatives', source: 'error' }];
                      }
                      
                      setSuggestions(allSuggestions);
                      console.log('Set alternative suggestions:', allSuggestions);
                      console.log('showSuggestions state should remain true');
                      // Force re-render by ensuring showSuggestions stays true
                      setShowSuggestions(true);
                    }}
                  >
                    No, show alternatives
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Group suggestions by source */}
                {suggestions.filter(s => (typeof s === 'object' ? s.source === 'spellcheck' : true)).length > 0 && (
                  <>
                    <div className="suggestion-category-header">Spelling Suggestions</div>
                    {suggestions
                      .filter(s => (typeof s === 'object' ? s.source === 'spellcheck' : true))
                      .map((suggestion, index) => (
                        <div
                          key={`spell-${index}`}
                          className="suggestion-item spellcheck-suggestion"
                          onClick={() => handleSuggestionSelect(suggestion)}
                        >
                          {typeof suggestion === 'object' ? suggestion.value : suggestion}
                        </div>
                      ))
                    }
                  </>
                )}
                
                {/* Database suggestions */}
                {suggestions.filter(s => typeof s === 'object' && s.source === 'database').length > 0 && (
                  <>
                    <div className="suggestion-category-header">Related Medical Products</div>
                    {suggestions
                      .filter(s => typeof s === 'object' && s.source === 'database')
                      .map((suggestion, index) => (
                        <div
                          key={`db-${index}`}
                          className="suggestion-item database-suggestion"
                          onClick={() => handleSuggestionSelect(suggestion)}
                          title={`Category: ${suggestion.typeName}`}
                        >
                          <div className="suggestion-value">{suggestion.value}</div>
                        </div>
                      ))
                    }
                  </>
                )}
                
                {/* Fallback message when no suggestions found */}
                {suggestions.length === 0 && (
                  <div className="suggestion-item">
                    No suggestions available
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MedicalSpellChecker;
