import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2, Edit3, Send, Check } from 'lucide-react';
import SpellCheckedTextArea from './SpellCheckedTextArea';
import SpellCheckedSOAPField from './SpellCheckedSOAPField';

// AmiriFont.js - Simplified approach without external dependencies
export const loadAmiriFont = async () => {
  // Since external fonts are causing issues, we'll return false
  // and handle Arabic text differently
  console.log('Font loading skipped - will use alternative approach');
  return false;
};

// Dynamic backend URL selection
const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:5001'
    : 'https://soap-598q.onrender.com');

export default function SOAPRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [soapNote, setSoapNote] = useState(null);
  // Explicit spell-check triggers
  const [checkTranscriptNow, setCheckTranscriptNow] = useState(false);
  const [checkSoapNow, setCheckSoapNow] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [language, setLanguage] = useState('en'); // 'en' or 'ar' 
  const [isEditingSOAP, setIsEditingSOAP] = useState(false);
  const [editedSOAPNote, setEditedSOAPNote] = useState(null);
  const [userAgreement, setUserAgreement] = useState(false);
  const [writeMode, setWriteMode] = useState(false);
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        processAudio(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Please allow microphone access to record audio.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (blob) => {
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('audio', blob, 'recording.webm');
    formData.append('language', language);

    try {
      // Send to backend for transcription
      const response = await fetch(`${BACKEND_URL}/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Transcription failed');
      
      const data = await response.json();
      setTranscript(data.transcript);
      setEditedTranscript(data.transcript);
    } catch (error) {
      console.error('Error processing audio:', error);
      alert('Failed to process audio. Please check if the backend server is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  const generateSOAPNote = async () => {
    setIsProcessing(true);
    try {
      // prevent checking current display while generating
      setCheckTranscriptNow(false);
      setCheckSoapNow(false);
      const response = await fetch(`${BACKEND_URL}/generate-soap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transcript: editedTranscript, language }),
      });

      if (!response.ok) throw new Error('SOAP note generation failed');
      
      const data = await response.json();
      // Support new structure: { soapNote: { soap_note: { ... } } } or { soapNote: { ... } }
      let note = data.soapNote;
      if (note && note.soap_note) note = note.soap_note;
      // Fallback to old structure if needed
      setSoapNote(note);
      setEditedSOAPNote(note);
      setUserAgreement(false);
      
      // Do NOT auto-check here. User can press "Check SOAP Spelling" button explicitly.
      // If you want a single auto-check after generation, uncomment:
      // setTimeout(() => setCheckSoapNow(v => !v), 0);
    } catch (error) {
      console.error('Error generating SOAP note:', error);
      alert('Failed to generate SOAP note. Please check if the backend server is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Helper: Remove unmentioned fields/sections (same logic as backend)
  function cleanSOAPNote(note) {
    if (!note || typeof note !== 'object') return note;
    const isUnmentioned = (val) => {
      if (!val) return true;
      if (typeof val === 'string') {
        const valLower = val.trim().toLowerCase();
        const phrases = [
          'not mentioned', 'not discussed', 'not addressed',
          'no known', 'no current', 'pending clinical examination',
          'vital signs not available', 'no medications prescribed currently',
          'no known allergies', 'no current medications', 'not available currently',
          'not specified', 'not available', 'none', 'n/a', 'na',
          'لم يذكر', 'لم يتم التطرق', 'لا يتناول أدوية حالياً',
          'لا يوجد تاريخ مرضي مزمن', 'بانتظار الفحص السريري',
          'العلامات الحيوية غير متوفرة حالياً', 'لم يتم وصف أدوية حالياً',
          'لم يتم التطرق لهذه النقاط أثناء اللقاء', 'غير متوفرة حالياً',
          'غير محدد', 'غير متوفر', 'لا يوجد', 'غير متاح', 'غير معروف',
          'غير مذكور', 'غير محدد في المحادثة', 'لم يتم ذكره',
          'غير متوفر حالياً', 'غير محدد في المحادثة', 'غير متوفر في المحادثة'
        ];
        return phrases.some(p => valLower.includes(p));
      }
      if (Array.isArray(val)) {
        // Remove empty/unmentioned items
        const filtered = val.filter(item => !isUnmentioned(item));
        return filtered.length === 0;
      }
      if (typeof val === 'object') {
        // Recursively clean
        const sub = cleanSOAPNote(val);
        return !sub || Object.keys(sub).length === 0;
      }
      return false;
    };
    const cleaned = {};
    for (const [k, v] of Object.entries(note)) {
      if (v == null) continue;
      if (Array.isArray(v)) {
        const filtered = v.filter(item => !isUnmentioned(item));
        if (filtered.length > 0) cleaned[k] = filtered;
      } else if (typeof v === 'object' && v !== null) {
        const sub = cleanSOAPNote(v);
        if (sub && Object.keys(sub).length > 0) cleaned[k] = sub;
      } else if (!isUnmentioned(v)) {
        cleaned[k] = v;
      }
    }
    return cleaned;
  }

  const SOAPSection = ({ title, data, sectionKey, isEditing, onEdit, language, onMainEditModeChange }) => {
    // State to manage individual field edit modes
    const [fieldEditModes, setFieldEditModes] = useState({});

    const handleFieldEditModeChange = (fieldKey, isFieldEditing, metadata = {}) => {
      setFieldEditModes(prev => ({
        ...prev,
        [`${sectionKey}_${fieldKey}`]: isFieldEditing
      }));

      // If this is triggered by a suggestion click, activate main SOAP edit mode
      if (isFieldEditing && metadata.triggeredBySuggestion && onMainEditModeChange) {
        onMainEditModeChange(true);
      }
    };
    const renderValue = (key, value) => {
      if (!value || value === '') return null;
      
      // Handle arrays
      if (Array.isArray(value)) {
        if (value.length === 0) return null;
        // If array of objects
        if (typeof value[0] === 'object' && value[0] !== null) {
          return (
            <div className="mt-2 space-y-6">
              {value.map((obj, idx) => {
                // Separate the 'name' field
                const entries = Object.entries(obj);
                const nameEntry = entries.find(([k]) => k.toLowerCase() === 'name');
                const otherEntries = entries.filter(([k]) => k.toLowerCase() !== 'name');
                return (
                  <div key={idx} className="space-y-2 bg-white rounded-lg p-3 shadow-sm border border-gray-200 flex flex-col items-center">
                    {nameEntry && (
                      <div className="text-base font-bold text-blue-900 mb-2 text-center w-full max-w-md">
                        {/* Run spell-check on the medication name just like other fields */}
                        <SpellCheckedSOAPField
                          value={String(nameEntry[1])}
                          onChange={(newValue) => {
                            // update only the 'name' of this medication card
                            const updated = value.map((item, i) =>
                              i === idx ? { ...item, [nameEntry[0]]: newValue } : item
                            );
                            // persist change into edited SOAP if currently editing, else into base note
                            if (isEditing) {
                              onEdit(sectionKey, key, updated);
                            } else {
                              onEdit(sectionKey, key, updated);
                            }
                          }}
                          isEditing={false}
                          onEditModeChange={() => {}}
                          language={language}
                          className="w-full"
                          checkNow={checkSoapNow}
                        />
                      </div>
                    )}
                    <div className="w-full max-w-md mx-auto">
                      {otherEntries.map(([subKey, subValue]) => (
                        <div key={subKey} className="flex flex-row justify-between items-center w-full mb-1">
                          <span className="text-xs font-bold text-gray-700 w-32 text-right pr-2">
                            {subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                          </span>
                          <div className="text-gray-700 w-56 text-left pl-2">
                            <SpellCheckedSOAPField
                              value={String(subValue)}
                              onChange={(newValue) => {
                                const updated = value.map((item, i) =>
                                  i === idx ? { ...item, [subKey]: newValue } : item
                                );
                                onEdit(sectionKey, key, updated);
                              }}
                              isEditing={false}
                              onEditModeChange={() => {}}
                              language={language}
                              className="w-full"
                              checkNow={checkSoapNow}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        } else {
          // Array of strings/numbers
          return <span className="text-gray-800 ml-2 text-center">{value.join(', ')}</span>;
        }
      }

      // Handle single objects
      if (typeof value === 'object' && value !== null) {
        return (
          <div className="mt-2 space-y-1">
            {Object.entries(value).map(([subKey, subValue]) => (
              <div key={subKey} className="flex flex-col items-center">
                <span className="text-xs font-bold text-gray-700">
                  {subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <span className="text-gray-700 ml-2">{String(subValue)}</span>
              </div>
            ))}
          </div>
        );
      }
      // Handle string/number values
      return <span className="text-gray-800 ml-2 text-center">{String(value)}</span>;
    };

    // Helper for editing arrays of objects
    const renderEditableArrayOfObjects = (arr, fieldKey) => (
      <div className="space-y-4 w-full">
        {arr.map((obj, idx) => (
          <div key={idx} className="flex flex-col items-center bg-white rounded-lg p-3 shadow-sm border border-gray-200">
            {Object.entries(obj).map(([subKey, subValue]) => (
              <div key={subKey} className="flex flex-col items-center w-full mb-2">
                <span className="text-xs font-bold text-gray-700 mb-1">
                  {subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <input
                  type="text"
                  value={subValue}
                  onChange={e => {
                    const updatedArr = arr.map((item, i) =>
                      i === idx ? { ...item, [subKey]: e.target.value } : item
                    );
                    onEdit(sectionKey, fieldKey, updatedArr);
                  }}
                  className="border border-gray-300 rounded px-2 py-1 text-sm w-full max-w-xs text-center"
                />
              </div>
            ))}
          </div>
        ))}
      </div>
    );

    // Helper for editing nested objects
    const renderEditableObject = (obj, fieldKey) => (
      <div className="space-y-2 w-full">
        {Object.entries(obj).map(([subKey, subValue]) => (
          <div key={subKey} className="flex flex-col items-center w-full">
            <span className="text-xs font-bold text-gray-700 mb-1">
              {subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
            </span>
            <input
              type="text"
              value={subValue}
              onChange={e => {
                onEdit(sectionKey, fieldKey, { ...obj, [subKey]: e.target.value });
              }}
              className="border border-gray-300 rounded px-2 py-1 text-sm w-full max-w-xs text-center"
            />
          </div>
        ))}
      </div>
    );

    // Special handling for Objective section - always show it even if empty
    if (title === "OBJECTIVE" && (!data || Object.keys(data).length === 0)) {
      return (
        <div className="mb-10 objective">
          <div className="bg-gray-50 rounded-xl shadow-md px-8 py-8 flex flex-col items-center">
            <h3 className="text-xl font-bold text-blue-900 mb-6 text-center tracking-wide uppercase letter-spacing-wider">{title}</h3>
            <div className="space-y-6 w-full">
              <div className="text-gray-500 text-center italic">No objective data recorded</div>
            </div>
          </div>
        </div>
      );
    }
    
    if (!data || Object.keys(data).length === 0) return null;

    // Determine the CSS class based on the section title
    const getSectionClass = (title) => {
      switch (title) {
        case 'SUBJECTIVE': return 'subjective';
        case 'OBJECTIVE': return 'objective';
        case 'ASSESSMENT': return 'assessment';
        case 'PLAN': return 'plan';
        default: return '';
      }
    };

    return (
      <div className={`mb-10 ${getSectionClass(title)}`}>
        <div className="bg-gray-50 rounded-xl shadow-md px-8 py-8 flex flex-col items-center">
          <h3 className="text-xl font-bold text-blue-900 mb-6 text-center tracking-wide uppercase letter-spacing-wider">{title}</h3>
          <div className="space-y-6 w-full">
            {Object.entries(data).map(([key, value]) => {
              if (!value || value === '') return null;
              // Render editable array of objects
              if (isEditing && Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
                return (
                  <div key={key} className="flex flex-col items-center w-full">
                    <div className="text-base font-bold text-gray-800 mb-1 text-center">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                    </div>
                    {renderEditableArrayOfObjects(value, key)}
                  </div>
                );
              }
              // Render editable nested object
              if (isEditing && typeof value === 'object' && value !== null && !Array.isArray(value)) {
                return (
                  <div key={key} className="flex flex-col items-center w-full">
                    <div className="text-base font-bold text-gray-800 mb-1 text-center">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                    </div>
                    {renderEditableObject(value, key)}
                  </div>
                );
              }
              return (
                <div key={key} className="flex flex-col items-center w-full">
                  <div className="text-base font-bold text-gray-800 mb-1 text-center">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                  </div>
                  <div className="text-gray-800 w-full flex justify-center">
                    {isEditing || fieldEditModes[`${sectionKey}_${key}`] ? (
                      <SpellCheckedSOAPField
                        value={editedSOAPNote[sectionKey]?.[key] || value}
                        onChange={(newValue) => onEdit(sectionKey, key, newValue)}
                        isEditing={true}
                        onEditModeChange={(isFieldEditing, metadata) => handleFieldEditModeChange(key, isFieldEditing, metadata)}
                        language={language}
                        placeholder={`Enter ${key.replace(/_/g, ' ')}`}
                        className="w-full max-w-md"
                        checkNow={checkSoapNow}
                      />
                    ) : (
                      // Only use SpellCheckedSOAPField for string values, not objects or arrays
                      typeof value === 'string' || typeof value === 'number' ? (
                        <SpellCheckedSOAPField
                          value={String(value)}
                          onChange={(newValue) => onEdit(sectionKey, key, newValue)}
                          isEditing={false}
                          onEditModeChange={(isFieldEditing, metadata) => handleFieldEditModeChange(key, isFieldEditing, metadata)}
                          language={language}
                          className="w-full max-w-md"
                          checkNow={checkSoapNow}
                        />
                      ) : (
                        // For objects and arrays, use regular rendering
                        renderValue(key, value)
                      )
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // Handle SOAP note editing
  const handleSOAPEdit = (sectionKey, fieldKey, value) => {
    if (sectionKey === 'metadata') {
      // Handle metadata fields separately
      setEditedSOAPNote(prev => ({
        ...prev,
        [fieldKey]: value
      }));
    } else {
      setEditedSOAPNote(prev => ({
        ...prev,
        [sectionKey]: {
          ...prev[sectionKey],
          [fieldKey]: value
        }
      }));
    }
  };

  // Save SOAP note edits
  const saveSOAPEdits = () => {
    setSoapNote(editedSOAPNote);
    setIsEditingSOAP(false);
    window.soapNoteForDownload = editedSOAPNote;
  };

  // Handle main SOAP edit mode activation (triggered by suggestion clicks)
  const handleMainEditModeChange = (shouldEdit) => {
    if (shouldEdit) {
      setIsEditingSOAP(true);
      // Ensure editedSOAPNote is initialized with current SOAP note data
      if (!editedSOAPNote) {
        setEditedSOAPNote(soapNote);
      }
    }
  };

  // Helper function to format nested values for text output
  function formatValueForText(value, indent = '') {
    if (value === null || value === undefined) return 'None';
    if (typeof value === 'string' || typeof value === 'number') return String(value);
    
    if (Array.isArray(value)) {
      if (value.length === 0) return 'None';
      
      // Handle array of objects
      if (typeof value[0] === 'object' && value[0] !== null) {
        return value.map((obj, idx) => {
          const entries = Object.entries(obj);
          const nameEntry = entries.find(([k]) => k.toLowerCase() === 'name');
          const otherEntries = entries.filter(([k]) => k.toLowerCase() !== 'name');
          
          let result = '';
          if (nameEntry) {
            result += `${indent}${nameEntry[1]}\n`;
          }
          otherEntries.forEach(([subKey, subValue]) => {
            const formattedKey = subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            result += `${indent}  ${formattedKey}: ${formatValueForText(subValue, indent + '    ')}\n`;
          });
          return result;
        }).join('\n');
      } else {
        // Array of strings/numbers
        return value.join(', ');
      }
    }
    
    if (typeof value === 'object') {
      const entries = Object.entries(value);
      if (entries.length === 0) return 'None';
      
      return entries.map(([subKey, subValue]) => {
        const formattedKey = subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        return `${indent}${formattedKey}: ${formatValueForText(subValue, indent + '  ')}`;
      }).join('\n');
    }
    
    return String(value);
  }

  // Helper function to format SOAP note as plain text
  function formatSOAPNoteAsText(soapNote) {
    const sectionTitles = {
      subjective: 'SUBJECTIVE',
      objective: 'OBJECTIVE',
      assessment: 'ASSESSMENT',
      plan: 'PLAN',
    };
    let text = '';
    for (const section of Object.keys(sectionTitles)) {
      text += `\n${sectionTitles[section]}\n`;
      text += '-'.repeat(sectionTitles[section].length) + '\n';
      for (const [key, value] of Object.entries(soapNote[section] || {})) {
        const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const formattedValue = formatValueForText(value);
        text += `${formattedKey}: ${formattedValue}\n`;
      }
      text += '\n';
    }
    return text.trim();
  }

  // Check if content is Arabic
  const checkArabic = (obj) => {
    if (!obj) return false;
    return Object.values(obj).some(val => 
      val && /[\u0600-\u06FF]/.test(String(val))
    );
  };

  // Download handler with HTML print solution for Arabic
  function downloadSOAPNote(format) {
    const currentSOAPNote = editedSOAPNote || soapNote;
    if (!currentSOAPNote) return;
    
    const isArabic = checkArabic(currentSOAPNote.subjective) || 
                     checkArabic(currentSOAPNote.objective) || 
                     checkArabic(currentSOAPNote.assessment) || 
                     checkArabic(currentSOAPNote.plan);
    
    if (format === 'txt') {
      const text = formatSOAPNoteAsText(currentSOAPNote);
      const blob = new Blob([text], { type: 'text/plain; charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'SOAP_Note.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (format === 'pdf') {
      // Use HTML print solution for better Arabic support
      if (isArabic) {
        import('./ArabicPDFGenerator').then(module => {
          module.generateArabicPDF(currentSOAPNote);
        }).catch(error => {
          console.error('Error loading Arabic PDF generator:', error);
          alert('Error loading Arabic PDF generator. Please try the TXT download option.');
        });
      } else {
        import('./ArabicPDFGenerator').then(module => {
          module.generateEnglishPDF(currentSOAPNote);
        }).catch(error => {
          console.error('Error loading PDF generator:', error);
          // Fallback to jsPDF for English content
          downloadWithJsPDF(currentSOAPNote);
        });
      }
    }
  }

  // Fallback jsPDF function for English content
  function downloadWithJsPDF(soapNote) {
    import('jspdf').then((jsPDFModule) => {
      try {
        const { jsPDF } = jsPDFModule;
        const doc = new jsPDF({
          orientation: 'portrait',
          unit: 'pt',
          format: 'a4'
        });
        
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 40;
        let yPosition = 40;
        
        // Title
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        const title = 'SOAP Note Template';
        const titleWidth = doc.getTextWidth(title);
        doc.text(title, (pageWidth - titleWidth) / 2, yPosition);
        yPosition += 40;
        
        // Calculate dimensions for 2x2 grid
        const gridWidth = pageWidth - (margin * 2);
        const gridHeight = pageHeight - yPosition - margin;
        const cellWidth = gridWidth / 2;
        const cellHeight = gridHeight / 2;
        const cellPadding = 15;
        
        // Draw grid lines
        doc.setDrawColor(0, 0, 0);
        doc.setLineWidth(1);
        
        // Vertical line
        doc.line(pageWidth / 2, yPosition, pageWidth / 2, yPosition + gridHeight);
        // Horizontal line
        doc.line(margin, yPosition + gridHeight / 2, pageWidth - margin, yPosition + gridHeight / 2);
        // Border
        doc.rect(margin, yPosition, gridWidth, gridHeight);
        
        // Define sections with their positions
        const sections = [
          { 
            title: 'Subjective Section', 
            data: soapNote.subjective,
            x: margin + cellPadding,
            y: yPosition + cellPadding,
            width: cellWidth - (cellPadding * 2),
            height: cellHeight - (cellPadding * 2)
          },
          { 
            title: 'Objective Section', 
            data: soapNote.objective,
            x: margin + cellWidth + cellPadding,
            y: yPosition + cellPadding,
            width: cellWidth - (cellPadding * 2),
            height: cellHeight - (cellPadding * 2)
          },
          { 
            title: 'Assessment Section', 
            data: soapNote.assessment,
            x: margin + cellPadding,
            y: yPosition + cellHeight + cellPadding,
            width: cellWidth - (cellPadding * 2),
            height: cellHeight - (cellPadding * 2)
          },
          { 
            title: 'Plan Section', 
            data: soapNote.plan,
            x: margin + cellWidth + cellPadding,
            y: yPosition + cellHeight + cellPadding,
            width: cellWidth - (cellPadding * 2),
            height: cellHeight - (cellPadding * 2)
          }
        ];
        
        // Render each section
        sections.forEach(section => {
          if (section.data && Object.keys(section.data).length > 0) {
            let currentY = section.y;
            
            // Section title
            doc.setFontSize(12);
            doc.setFont('helvetica', 'bold');
            doc.text(section.title, section.x, currentY);
            currentY += 20;
            
            // Section content
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            
            Object.entries(section.data).forEach(([key, value]) => {
              if (value && currentY < section.y + section.height - 15) {
                // Format the key
                const formattedKey = key
                  .replace(/_/g, ' ')
                  .split(' ')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ');
                
                // Key in bold
                doc.setFont('helvetica', 'bold');
                doc.text(`${formattedKey}:`, section.x, currentY);
                currentY += 12;
                
                // Value in normal font
                doc.setFont('helvetica', 'normal');
                const processedValue = String(value);
                
                // Wrap text to fit in cell
                const lines = doc.splitTextToSize(processedValue, section.width - 10);
                const maxLines = Math.floor((section.y + section.height - currentY) / 12);
                const linesToShow = lines.slice(0, maxLines);
                
                linesToShow.forEach(line => {
                  if (currentY < section.y + section.height - 10) {
                    doc.text(line, section.x + 5, currentY);
                    currentY += 12;
                  }
                });
                
                if (lines.length > linesToShow.length) {
                  doc.text('...', section.x + 5, currentY);
                }
                
                currentY += 8; // Space between items
              }
            });
          } else {
            // Show "No data" for empty sections
            doc.setFontSize(12);
            doc.setFont('helvetica', 'bold');
            doc.text(section.title, section.x, section.y);
            doc.setFontSize(10);
            doc.setFont('helvetica', 'italic');
            doc.text('No data available', section.x, section.y + 25);
          }
        });
        
        // Save the PDF
        doc.save('SOAP_Note.pdf');
        
      } catch (error) {
        console.error('PDF generation error:', error);
        alert('Error generating PDF.');
      }
    }).catch(error => {
      console.error('Error loading jsPDF:', error);
      alert('Error loading PDF library. Please try again.');
    });
  }

  // Store soapNote globally for download
  useEffect(() => {
    if (editedSOAPNote) {
      window.soapNoteForDownload = editedSOAPNote;
    }
  }, [editedSOAPNote]);

  // Load Arabic font on component mount
  useEffect(() => {
    loadAmiriFont().then(loaded => {
      console.log('Arabic font loaded:', loaded);
    });
  }, []);

  // In the SOAP Note Display section, before rendering, clean the note:
  const displaySOAPNote = soapNote ? {
    ...cleanSOAPNote(soapNote),
    // Always ensure objective section exists
    objective: soapNote.objective || {}
  } : null;
  const displayEditedSOAPNote = editedSOAPNote ? {
    ...cleanSOAPNote(editedSOAPNote),
    // Always ensure objective section exists
    objective: editedSOAPNote.objective || {}
  } : null;

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container max-w-4xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">SOAP Note Generator</h1>
          <p className="text-gray-600 mt-2">Record audio and generate a structured SOAP note</p>
          
          {/* Language Selector */}
          <div className="mt-4 inline-flex bg-white rounded-lg p-1 shadow-sm">
            <button
              onClick={() => setLanguage('en')}
              className={`px-4 py-2 rounded-md transition ${
                language === 'en' 
                  ? 'bg-blue-500 text-white' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('ar')}
              className={`px-4 py-2 rounded-md transition ${
                language === 'ar' 
                  ? 'bg-blue-500 text-white' 
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              العربية
            </button>
          </div>
        </div>

        {/* Recording Section */}
        {!writeMode && (
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <div className="flex flex-col items-center">
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isProcessing}
                className={`p-8 rounded-full transition-all transform hover:scale-110 ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
                    : 'bg-blue-500 hover:bg-blue-600'
                } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {isRecording ? (
                  <MicOff className="w-12 h-12 text-white" />
                ) : (
                  <Mic className="w-12 h-12 text-white" />
                )}
              </button>
              <p className="mt-4 text-gray-600">
                {isRecording ? 'Recording... Click to stop' : 'Click to start recording'}
              </p>
              <button
                onClick={() => setWriteMode(true)}
                className="mt-6 px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-medium transition"
              >
                Write Instead
              </button>
            </div>
          </div>
        )}

        {/* Write Mode Section */}
        {writeMode && (
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <div className="flex flex-col items-center">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Type or Paste Transcript</h2>
              <div className="w-full mb-4">
                <div className="flex justify-end mb-2">
                  <button
                    onClick={() => setCheckTranscriptNow(v => !v)}
                    className="px-3 py-1 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded-md"
                    title="Run spell check for transcript"
                  >
                    Check Transcript Spelling
                  </button>
                </div>
                <SpellCheckedTextArea
                  value={editedTranscript}
                  onChange={(newValue) => {
                    setTranscript(newValue);
                    setEditedTranscript(newValue);
                  }}
                  placeholder="Type or paste your transcript here..."
                  language={language}
                  enableSpellCheck={true}
                  rows={10}
                  checkNow={checkTranscriptNow}
                />
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => setWriteMode(false)}
                  className="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-lg font-medium transition"
                >
                  Back to Recording
                </button>
                <button
                  onClick={generateSOAPNote}
                  disabled={isProcessing || !editedTranscript.trim()}
                  className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Generate SOAP Note
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Transcript Section */}
        {transcript && !writeMode && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="relative mb-4">
              <h2 className="text-xl font-semibold text-gray-800 text-center">Transcript</h2>
            </div>
            
            <div className="flex justify-end mb-2">
              <button
                onClick={() => setCheckTranscriptNow(v => !v)}
                className="px-3 py-1 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded-md"
                title="Run spell check for transcript"
              >
                Check Transcript Spelling
              </button>
            </div>
            <SpellCheckedTextArea
              value={editedTranscript}
              onChange={(newValue) => setEditedTranscript(newValue)}
              placeholder="Transcript will appear here..."
              language={language}
              enableSpellCheck={true}
              rows={8}
              checkNow={checkTranscriptNow}
            />
            
            <button
              onClick={generateSOAPNote}
              disabled={isProcessing}
              className="mt-4 flex items-center gap-2 px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Generate SOAP Note
                </>
              )}
            </button>
          </div>
        )}

        {/* SOAP Note Display */}
        {displaySOAPNote && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="relative mb-6">
              <h2 className="text-2xl font-bold text-gray-800 text-center">SOAP Note</h2>
              <div className="absolute right-0 -top-10 flex gap-2">
                <button
                  onClick={() => setCheckSoapNow(v => !v)}
                  className="px-3 py-1 text-sm bg-indigo-500 hover:bg-indigo-600 text-white rounded-md"
                  title="Run spell check for SOAP note"
                >
                  Check SOAP Spelling
                </button>
              </div>
              {/* Show metadata if present - now editable */}
              {displaySOAPNote.patient_id && (
                <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600 text-center space-y-2">
                    {isEditingSOAP ? (
                      <div className="space-y-2">
                        <div className="flex justify-center items-center space-x-4">
                          <span>Patient ID: <input 
                            type="text" 
                            value={editedSOAPNote.patient_id || displaySOAPNote.patient_id} 
                            onChange={(e) => handleSOAPEdit('metadata', 'patient_id', e.target.value)}
                            className="border border-gray-300 rounded px-2 py-1 text-xs"
                          /></span>
                          <span>Date: <input 
                            type="text" 
                            value={editedSOAPNote.visit_date || displaySOAPNote.visit_date} 
                            onChange={(e) => handleSOAPEdit('metadata', 'visit_date', e.target.value)}
                            className="border border-gray-300 rounded px-2 py-1 text-xs"
                          /></span>
                          <span>Provider: <input 
                            type="text" 
                            value={editedSOAPNote.provider_name || displaySOAPNote.provider_name || 'Not mentioned'} 
                            onChange={(e) => handleSOAPEdit('metadata', 'provider_name', e.target.value)}
                            className="border border-gray-300 rounded px-2 py-1 text-xs"
                          /></span>
                        </div>
                        {displaySOAPNote.patient_name && displaySOAPNote.patient_name !== "Unknown" && displaySOAPNote.patient_name !== "غير محدد" && (
                          <div className="flex justify-center items-center space-x-4">
                            <span>Patient: <input 
                              type="text" 
                              value={editedSOAPNote.patient_name || displaySOAPNote.patient_name} 
                              onChange={(e) => handleSOAPEdit('metadata', 'patient_name', e.target.value)}
                              className="border border-gray-300 rounded px-2 py-1 text-xs"
                            /></span>
                            {displaySOAPNote.patient_age && displaySOAPNote.patient_age !== "Unknown" && displaySOAPNote.patient_age !== "غير محدد" && (
                              <span>Age: <input 
                                type="text" 
                                value={editedSOAPNote.patient_age || displaySOAPNote.patient_age} 
                                onChange={(e) => handleSOAPEdit('metadata', 'patient_age', e.target.value)}
                                className="border border-gray-300 rounded px-2 py-1 text-xs"
                              /></span>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <>
                        <div className="flex justify-center items-center space-x-4">
                          <span>Patient ID: {displaySOAPNote.patient_id}</span>
                          <span>Date: {displaySOAPNote.visit_date}</span>
                          <span>Provider: {displaySOAPNote.provider_name || 'Not mentioned'}</span>
                        </div>
                        {displaySOAPNote.patient_name && displaySOAPNote.patient_name !== "Unknown" && displaySOAPNote.patient_name !== "غير محدد" && (
                          <div className="flex justify-center items-center space-x-2">
                            <span>Patient: {displaySOAPNote.patient_name}</span>
                            {displaySOAPNote.patient_age && displaySOAPNote.patient_age !== "Unknown" && displaySOAPNote.patient_age !== "غير محدد" && (
                              <span>Age: {displaySOAPNote.patient_age}</span>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}
              {!soapNote.raw_response && (
                <button
                  onClick={() => {
                    if (isEditingSOAP) {
                      saveSOAPEdits();
                    } else {
                      setIsEditingSOAP(true);
                    }
                  }}
                  className="absolute right-0 top-0 flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                >
                  {isEditingSOAP ? (
                    <>
                      <Check className="w-4 h-4" />
                      Save
                    </>
                  ) : (
                    <>
                      <Edit3 className="w-4 h-4" />
                      Edit
                    </>
                  )}
                </button>
              )}
            </div>
            
            {/* Check if this is a raw response */}
            {soapNote.raw_response ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                <div className="flex items-center mb-2">
                  <div className="w-4 h-4 bg-yellow-400 rounded-full mr-2"></div>
                  <span className="font-medium text-yellow-800">Raw Response - Could not parse as structured SOAP note</span>
                </div>
                <div className="text-gray-700 whitespace-pre-wrap font-mono text-sm bg-white p-3 rounded border">
                  {soapNote.raw_response}
                </div>
                <p className="text-sm text-yellow-700 mt-2">
                  The AI response could not be parsed as structured JSON. This might be due to extra text or formatting issues. 
                  You can still copy the content above and format it manually.
                </p>
              </div>
            ) : (
              <>
                <div className="soap_data">
                  {/* SUBJECTIVE Section */}
                  <SOAPSection 
                    title="SUBJECTIVE" 
                    data={isEditingSOAP ? displayEditedSOAPNote?.subjective : displaySOAPNote.subjective} 
                    sectionKey="subjective"
                    isEditing={isEditingSOAP}
                    onEdit={handleSOAPEdit}
                    onMainEditModeChange={handleMainEditModeChange}
                    language={language}
                  />
                  {/* OBJECTIVE Section */}
                  <SOAPSection 
                    title="OBJECTIVE" 
                    data={isEditingSOAP ? displayEditedSOAPNote?.objective : displaySOAPNote.objective} 
                    sectionKey="objective"
                    isEditing={isEditingSOAP}
                    onEdit={handleSOAPEdit}
                    onMainEditModeChange={handleMainEditModeChange}
                    language={language}
                  />
                  {/* ASSESSMENT Section */}
                  <SOAPSection 
                    title="ASSESSMENT" 
                    data={isEditingSOAP ? displayEditedSOAPNote?.assessment : displaySOAPNote.assessment} 
                    sectionKey="assessment"
                    isEditing={isEditingSOAP}
                    onEdit={handleSOAPEdit}
                    onMainEditModeChange={handleMainEditModeChange}
                    language={language}
                  />
                  {/* PLAN Section */}
                  <SOAPSection 
                    title="PLAN" 
                    data={isEditingSOAP ? displayEditedSOAPNote?.plan : displaySOAPNote.plan} 
                    sectionKey="plan"
                    isEditing={isEditingSOAP}
                    onEdit={handleSOAPEdit}
                    onMainEditModeChange={handleMainEditModeChange}
                    language={language}
                  />
                </div>

                {/* User Agreement Checkbox */}
                {!isEditingSOAP && (
                  <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={userAgreement}
                        onChange={(e) => {
                          setUserAgreement(e.target.checked);
                          if (!e.target.checked) {
                            // Reset authentication when unchecking
                            setShowAuthForm(false);
                            setIsAuthenticated(false);
                            setUsername('');
                            setPassword('');
                            setAuthError('');
                          } else {
                            // Show auth form when checking
                            setShowAuthForm(true);
                          }
                        }}
                        className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">
                        I have reviewed and agree with the contents of this SOAP note. I understand that this document contains medical information and I am responsible for its accuracy and appropriate use.
                      </span>
                    </label>
                    
                    {/* Authentication Form */}
                    {showAuthForm && !isAuthenticated && (
                      <div className="mt-4 p-4 bg-white border border-gray-300 rounded-lg">
                        <h4 className="text-sm font-semibold text-gray-800 mb-3">Authentication Required</h4>
                        <div className="space-y-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Username
                            </label>
                            <input
                              type="text"
                              value={username}
                              onChange={(e) => setUsername(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              placeholder="Enter your username"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Password
                            </label>
                            <input
                              type="password"
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              placeholder="Enter your password"
                            />
                          </div>
                          {authError && (
                            <div className="text-red-600 text-xs">{authError}</div>
                          )}
                          <div className="flex gap-2">
                            <button
                              onClick={() => {
                                if (!username.trim() || !password.trim()) {
                                  setAuthError('Please enter both username and password');
                                  return;
                                }
                                // Simulate authentication (in real app, this would call an API)
                                setIsAuthenticated(true);
                                setShowAuthForm(false);
                                setAuthError('');
                              }}
                              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md transition"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => {
                                setShowAuthForm(false);
                                setUserAgreement(false);
                                setUsername('');
                                setPassword('');
                                setAuthError('');
                              }}
                              className="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 text-sm rounded-md transition"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Authentication Success Message */}
                    {isAuthenticated && (
                      <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-green-600" />
                          <span className="text-sm text-green-800">Authentication successful. You can now download the SOAP note.</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Download Buttons */}
                {!isEditingSOAP && (
                  <div className="flex gap-4 justify-center mt-6">
                    <button
                      onClick={() => downloadSOAPNote('txt')}
                      disabled={!userAgreement || !isAuthenticated}
                      className={`px-4 py-2 rounded-lg transition ${
                        userAgreement && isAuthenticated
                          ? 'bg-blue-500 hover:bg-blue-600 text-white cursor-pointer' 
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                      title={!userAgreement ? 'Please review and agree with the SOAP note contents before downloading' : 
                             !isAuthenticated ? 'Please complete authentication before downloading' : ''}
                    >
                      Download as TXT
                    </button>
                    <button
                      onClick={() => downloadSOAPNote('pdf')}
                      disabled={!userAgreement || !isAuthenticated}
                      className={`px-4 py-2 rounded-lg transition ${
                        userAgreement && isAuthenticated
                          ? 'bg-green-500 hover:bg-green-600 text-white cursor-pointer' 
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                      title={!userAgreement ? 'Please review and agree with the SOAP note contents before downloading' : 
                             !isAuthenticated ? 'Please complete authentication before downloading' : ''}
                    >
                      {/* Check if content is Arabic to show appropriate label */}
                      {(checkArabic(soapNote.subjective) || 
                        checkArabic(soapNote.objective) || 
                        checkArabic(soapNote.assessment) || 
                        checkArabic(soapNote.plan)) 
                        ? 'Print Arabic PDF' 
                        : 'Download as PDF'
                      }
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg flex items-center gap-4">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              <span className="text-lg">Processing audio...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
