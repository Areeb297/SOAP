import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2, Edit3, Send, Check } from 'lucide-react';

export default function SOAPRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [soapNote, setSoapNote] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [audioBlob, setAudioBlob] = useState(null);
  const [language, setLanguage] = useState('en'); // 'en' or 'ar'
  
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
        setAudioBlob(audioBlob);
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
      const response = await fetch('http://localhost:5001/transcribe', {
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
      const response = await fetch('http://localhost:5001/generate-soap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transcript: editedTranscript, language }),
      });

      if (!response.ok) throw new Error('SOAP generation failed');
      
      const data = await response.json();
      setSoapNote(data.soapNote);
    } catch (error) {
      console.error('Error generating SOAP note:', error);
      alert('Failed to generate SOAP note. Please check if the backend server is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  const SOAPSection = ({ title, data }) => {
    if (!data || Object.keys(data).length === 0) return null;
    
    const renderValue = (value) => {
      if (typeof value === 'object' && value !== null) {
        // Handle nested objects
        return (
          <div className="ml-4 mt-2 space-y-1">
            {Object.entries(value).map(([subKey, subValue]) => (
              <div key={subKey} className="flex flex-col">
                <span className="text-xs font-medium text-gray-500">
                  {subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <span className="text-gray-700 ml-2">{subValue}</span>
              </div>
            ))}
          </div>
        );
      }
      // Handle string values
      return <span className="text-gray-800 ml-2">{value}</span>;
    };
    
    return (
      <div className="mb-6 bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">{title}</h3>
        <div className="space-y-2">
          {Object.entries(data).map(([key, value]) => (
            value && (
              <div key={key} className="flex flex-col">
                <span className="text-sm font-medium text-gray-600">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                {renderValue(value)}
              </div>
            )
          ))}
        </div>
      </div>
    );
  };

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
        text += `${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: ${value}\n`;
      }
      text += '\n';
    }
    return text.trim();
  }

  // Helper function to load the Arabic font as base64 (if not already loaded)
  function ensureArabicFontLoaded() {
    if (!window.NotoNaskhArabicRegularTTF) {
      // Fetch the font as base64 from the public directory
      fetch('/fonts/NotoNaskhArabic-Regular.ttf')
        .then(response => response.arrayBuffer())
        .then(buffer => {
          // Convert to base64
          let binary = '';
          const bytes = new Uint8Array(buffer);
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          window.NotoNaskhArabicRegularTTF = btoa(binary);
        });
    }
  }

  // Download handler
  function downloadSOAPNote(format) {
    const soapNote = window.soapNoteForDownload || null;
    if (!soapNote) return;
    if (format === 'txt') {
      const text = formatSOAPNoteAsText(soapNote);
      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'SOAP_Note.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (format === 'pdf') {
      import('jspdf').then(jsPDFModule => {
        try {
          const { jsPDF } = jsPDFModule;
          const doc = new jsPDF();
          const pageWidth = doc.internal.pageSize.getWidth();
          const pageHeight = doc.internal.pageSize.getHeight();
          const margin = 10;
          const cellWidth = (pageWidth - margin * 2) / 2;
          const cellHeight = (pageHeight - margin * 2) / 2;

          // Detect if the SOAP note is in Arabic (simple check: are most fields Arabic?)
          const isArabic = Object.values(soapNote.subjective || {}).some(val => /[\u0600-\u06FF]/.test(val));
          let useArabicFont = false;
          
          // Always start with a safe font
          doc.setFont('helvetica', 'normal');
          
          if (isArabic) {
            try {
              if (window.NotoNaskhArabicRegularTTF) {
                doc.addFileToVFS('NotoNaskhArabic-Regular.ttf', window.NotoNaskhArabicRegularTTF);
                doc.addFont('NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic', 'normal');
                
                // Test the font by checking if it can render text properly
                const testText = 'Test';
                try {
                  doc.setFont('NotoNaskhArabic', 'normal');
                  // Try to get text width - this will fail if font has issues
                  doc.getTextWidth(testText);
                  useArabicFont = true;
                  console.log('Arabic font loaded successfully');
                } catch (fontTestError) {
                  console.warn('Arabic font test failed, using helvetica:', fontTestError);
                  doc.setFont('helvetica', 'normal');
                  useArabicFont = false;
                }
              } else {
                console.warn('Arabic font file not available. Using helvetica fallback.');
              }
            } catch (error) {
              console.error('Error loading Arabic font:', error);
              doc.setFont('helvetica', 'normal');
              useArabicFont = false;
            }
          }

          // Safe text rendering function
          const safeText = (text, x, y, options = {}) => {
            try {
              doc.text(text, x, y, options);
            } catch (error) {
              console.error('Text rendering error:', error);
              // Fallback: try with helvetica
              const currentFont = doc.getFont();
              try {
                doc.setFont('helvetica', 'normal');
                doc.text(text, x, y, options);
              } catch (fallbackError) {
                console.error('Fallback text rendering also failed:', fallbackError);
                // Last resort: render without options
                try {
                  doc.text(text, x, y);
                } catch (finalError) {
                  console.error('All text rendering attempts failed for:', text);
                }
              }
            }
          };

          doc.setFontSize(18);
          safeText(isArabic ? 'نموذج ملاحظة SOAP' : 'SOAP Note Template', pageWidth / 2, margin + 8, { align: 'center' });
          doc.setFontSize(12);
        // Draw grid
        doc.setLineWidth(0.5);
        // Vertical line
        doc.line(pageWidth / 2, margin + 12, pageWidth / 2, pageHeight - margin);
        // Horizontal line
        doc.line(margin, margin + 12 + cellHeight, pageWidth - margin, margin + 12 + cellHeight);
        // Outer border
        doc.rect(margin, margin + 12, pageWidth - margin * 2, pageHeight - margin * 2 - 12);
        // Section positions
        const sections = [
          { title: isArabic ? 'القسم الذاتي' : 'Subjective Section', x: margin + 2, y: margin + 18, data: soapNote.subjective },
          { title: isArabic ? 'القسم الموضوعي' : 'Objective Section', x: pageWidth / 2 + 2, y: margin + 18, data: soapNote.objective },
          { title: isArabic ? 'قسم التقييم' : 'Assessment Section', x: margin + 2, y: margin + 18 + cellHeight, data: soapNote.assessment },
          { title: isArabic ? 'قسم الخطة' : 'Plan Section', x: pageWidth / 2 + 2, y: margin + 18 + cellHeight, data: soapNote.plan },
        ];
        doc.setFontSize(13);
          sections.forEach(section => {
            try {
              // Set title font
              if (isArabic && useArabicFont) {
                try {
                  doc.setFont('NotoNaskhArabic', 'normal');
                } catch (fontError) {
                  doc.setFont('helvetica', 'bold');
                  useArabicFont = false;
                }
                safeText(section.title, section.x + cellWidth - 4, section.y, { align: 'right' });
              } else {
                doc.setFont('helvetica', 'bold');
                safeText(section.title, section.x, section.y);
              }
              
              // Set content font
              if (isArabic && useArabicFont) {
                try {
                  doc.setFont('NotoNaskhArabic', 'normal');
                } catch (fontError) {
                  doc.setFont('helvetica', 'normal');
                  useArabicFont = false;
                }
              } else {
                doc.setFont('helvetica', 'normal');
              }
              
              let y = section.y + 7;
              Object.entries(section.data || {}).forEach(([key, value]) => {
                let label;
                if (isArabic) {
                  label = `- ${value}`;
                } else {
                  label =
                    '- ' +
                    key
                      .replace(/_/g, ' ')
                      .replace(/\b\w/g, l => l.toUpperCase()) +
                    ': ' +
                    value;
                }
                
                // Safe text wrapping and rendering
                try {
                  const wrappedLines = doc.splitTextToSize(label, cellWidth - 6);
                  wrappedLines.forEach(line => {
                    if (isArabic && useArabicFont) {
                      safeText(line, section.x + cellWidth - 4, y, { align: 'right', maxWidth: cellWidth - 6 });
                    } else {
                      safeText(line, section.x, y, { maxWidth: cellWidth - 6 });
                    }
                    y += 6;
                  });
                } catch (textError) {
                  console.error('Error with text wrapping, using simple rendering:', textError);
                  // Fallback: render without text wrapping
                  if (isArabic && useArabicFont) {
                    safeText(label, section.x + cellWidth - 4, y, { align: 'right' });
                  } else {
                    safeText(label, section.x, y);
                  }
                  y += 6;
                }
              });
            } catch (sectionError) {
              console.error('Error rendering section:', sectionError);
              // Continue with next section
            }
          });
          doc.save('SOAP_Note.pdf');
        } catch (pdfError) {
          console.error('PDF generation error:', pdfError);
          alert('Error generating PDF. Please try again or use the TXT download option.');
        }
      }).catch(moduleError => {
        console.error('Error loading jsPDF module:', moduleError);
        alert('Error loading PDF library. Please refresh the page and try again.');
      });
    }
  }

  // Store soapNote globally for download
  useEffect(() => {
    if (soapNote) {
      window.soapNoteForDownload = soapNote;
    }
  }, [soapNote]);

  // Call this once on component mount
  useEffect(() => {
    ensureArabicFontLoaded();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
          SOAP Note Voice Recorder
        </h1>
        {/* Language Selector */}
        <div className="flex justify-center mb-6">
          <label className="mr-2 font-medium">Language:</label>
          <select
            value={language}
            onChange={e => setLanguage(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1"
          >
            <option value="en">English</option>
            <option value="ar">Arabic</option>
          </select>
        </div>

        {/* Recording Section */}
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
          </div>
        </div>

        {/* Transcript Section */}
        {transcript && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800">Transcript</h2>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
              >
                {isEditing ? (
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
            </div>
            
            {isEditing ? (
              <textarea
                value={editedTranscript}
                onChange={(e) => setEditedTranscript(e.target.value)}
                className="w-full h-40 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            ) : (
              <p className="text-gray-700 whitespace-pre-wrap">{editedTranscript}</p>
            )}
            
            <button
              onClick={generateSOAPNote}
              disabled={isProcessing || isEditing}
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
        {soapNote && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">SOAP Note</h2>
            
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
                <SOAPSection title="SUBJECTIVE" data={soapNote.subjective} />
                <SOAPSection title="OBJECTIVE" data={soapNote.objective} />
                <SOAPSection title="ASSESSMENT" data={soapNote.assessment} />
                <SOAPSection title="PLAN" data={soapNote.plan} />

                {/* Download Buttons */}
                <div className="flex gap-4 justify-center mt-6">
                  <button
                    onClick={() => downloadSOAPNote('txt')}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
                  >
                    Download as TXT
                  </button>
                  <button
                    onClick={() => downloadSOAPNote('pdf')}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition"
                  >
                    Download as PDF
                  </button>
                </div>
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