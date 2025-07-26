import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2, Edit3, Send, Check } from 'lucide-react';

// AmiriFont.js - Simplified approach without external dependencies
export const loadAmiriFont = async () => {
  // Since external fonts are causing issues, we'll return false
  // and handle Arabic text differently
  console.log('Font loading skipped - will use alternative approach');
  return false;
};

export default function SOAPRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [soapNote, setSoapNote] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedTranscript, setEditedTranscript] = useState('');
  const [audioBlob, setAudioBlob] = useState(null);
  const [language, setLanguage] = useState('en'); // 'en' or 'ar'
  const [arabicFontLoaded, setArabicFontLoaded] = useState(false);
  const [isEditingSOAP, setIsEditingSOAP] = useState(false);
  const [editedSOAPNote, setEditedSOAPNote] = useState(null);
  const [userAgreement, setUserAgreement] = useState(false);
  
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
      setEditedSOAPNote(data.soapNote);
      setUserAgreement(false);
    } catch (error) {
      console.error('Error generating SOAP note:', error);
      alert('Failed to generate SOAP note. Please check if the backend server is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  const SOAPSection = ({ title, data, sectionKey, isEditing, onEdit }) => {
    if (!data || Object.keys(data).length === 0) return null;
    
    const renderValue = (key, value) => {
      if (isEditing) {
        return (
          <textarea
            value={value || ''}
            onChange={(e) => onEdit(sectionKey, key, e.target.value)}
            className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows="2"
          />
        );
      }
      
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
            value !== null && value !== undefined && (
              <div key={key} className="flex flex-col">
                <span className="text-sm font-medium text-gray-600">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                {renderValue(key, value)}
              </div>
            )
          ))}
        </div>
      </div>
    );
  };

  // Handle SOAP note editing
  const handleSOAPEdit = (sectionKey, fieldKey, value) => {
    setEditedSOAPNote(prev => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        [fieldKey]: value
      }
    }));
  };

  // Save SOAP note edits
  const saveSOAPEdits = () => {
    setSoapNote(editedSOAPNote);
    setIsEditingSOAP(false);
    window.soapNoteForDownload = editedSOAPNote;
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
      setArabicFontLoaded(loaded);
      console.log('Arabic font loaded:', loaded);
    });
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
            <div className="relative mb-4">
              <h2 className="text-xl font-semibold text-gray-800 text-center">Transcript</h2>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="absolute right-0 top-0 flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
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
            <div className="relative mb-6">
              <h2 className="text-2xl font-bold text-gray-800 text-center">SOAP Note</h2>
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
                <SOAPSection 
                  title="SUBJECTIVE" 
                  data={isEditingSOAP ? editedSOAPNote?.subjective : soapNote.subjective} 
                  sectionKey="subjective"
                  isEditing={isEditingSOAP}
                  onEdit={handleSOAPEdit}
                />
                <SOAPSection 
                  title="OBJECTIVE" 
                  data={isEditingSOAP ? editedSOAPNote?.objective : soapNote.objective} 
                  sectionKey="objective"
                  isEditing={isEditingSOAP}
                  onEdit={handleSOAPEdit}
                />
                <SOAPSection 
                  title="ASSESSMENT" 
                  data={isEditingSOAP ? editedSOAPNote?.assessment : soapNote.assessment} 
                  sectionKey="assessment"
                  isEditing={isEditingSOAP}
                  onEdit={handleSOAPEdit}
                />
                <SOAPSection 
                  title="PLAN" 
                  data={isEditingSOAP ? editedSOAPNote?.plan : soapNote.plan} 
                  sectionKey="plan"
                  isEditing={isEditingSOAP}
                  onEdit={handleSOAPEdit}
                />

                {/* User Agreement Checkbox */}
                {!isEditingSOAP && (
                  <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={userAgreement}
                        onChange={(e) => setUserAgreement(e.target.checked)}
                        className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">
                        I have reviewed and agree with the contents of this SOAP note. I understand that this document contains medical information and I am responsible for its accuracy and appropriate use.
                      </span>
                    </label>
                  </div>
                )}

                {/* Download Buttons */}
                {!isEditingSOAP && (
                  <div className="flex gap-4 justify-center mt-6">
                    <button
                      onClick={() => downloadSOAPNote('txt')}
                      disabled={!userAgreement}
                      className={`px-4 py-2 rounded-lg transition ${
                        userAgreement 
                          ? 'bg-blue-500 hover:bg-blue-600 text-white cursor-pointer' 
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                      title={!userAgreement ? 'Please review and agree with the SOAP note contents before downloading' : ''}
                    >
                      Download as TXT
                    </button>
                    <button
                      onClick={() => downloadSOAPNote('pdf')}
                      disabled={!userAgreement}
                      className={`px-4 py-2 rounded-lg transition ${
                        userAgreement 
                          ? 'bg-green-500 hover:bg-green-600 text-white cursor-pointer' 
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                      title={!userAgreement ? 'Please review and agree with the SOAP note contents before downloading' : ''}
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