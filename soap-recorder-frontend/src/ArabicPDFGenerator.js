// ArabicPDFGenerator.js - HTML-based PDF generation for Arabic content
export function generateArabicPDF(soapNote) {
    // Helper function to format field names
    const formatFieldName = (key) => {
      const arabicLabels = {
        'chief_complaint': 'الشكوى الرئيسية',
        'history_of_present_illness': 'تاريخ المرض الحالي',
        'past_medical_history': 'التاريخ المرضي السابق',
        'family_history': 'التاريخ العائلي',
        'social_history': 'التاريخ الاجتماعي',
        'medications': 'الأدوية',
        'allergies': 'الحساسية',
        'vital_signs': 'العلامات الحيوية',
        'physical_examination_findings': 'نتائج الفحص السريري',
        'diagnosis': 'التشخيص',
        'differential_diagnosis': 'التشخيص التفريقي',
        'risk_factors': 'عوامل الخطر',
        'medications_prescribed': 'الأدوية الموصوفة',
        'investigations': 'الفحوصات',
        'patient_education_counseling': 'تثقيف وإرشاد المريض',
        'follow_up_instructions': 'تعليمات المتابعة'
      };
      
      return arabicLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };
  
    // Create HTML content with 2x2 grid layout
    const htmlContent = `
      <!DOCTYPE html>
      <html dir="rtl" lang="ar">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تقرير SOAP الطبي</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          
          body { 
            font-family: 'Segoe UI', Tahoma, Arial, sans-serif; 
            direction: rtl; 
            padding: 20px;
            line-height: 1.4;
            font-size: 11px;
            background: white;
          }
          
          .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
          }
          
          .header h1 {
            font-size: 20px;
            color: #333;
            margin-bottom: 5px;
          }
          
          .soap-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 2px;
            height: calc(100vh - 150px);
            border: 2px solid #000;
          }
          
          .soap-section {
            border: 1px solid #000;
            padding: 15px;
            overflow: hidden;
          }
          
          .soap-section h2 {
            font-size: 14px;
            color: #000;
            margin-bottom: 15px;
            text-align: center;
            font-weight: bold;
            border-bottom: 1px solid #666;
            padding-bottom: 8px;
          }
          
          .section-content {
            height: calc(100% - 45px);
            overflow: hidden;
          }
          
          .field-item {
            margin-bottom: 12px;
            line-height: 1.3;
          }
          
          .field-label {
            font-weight: bold;
            color: #333;
            font-size: 10px;
            margin-bottom: 3px;
            display: block;
          }
          
          .field-value {
            color: #000;
            font-size: 11px;
            margin-right: 10px;
            word-wrap: break-word;
            overflow-wrap: break-word;
          }
          
          .no-data {
            color: #666;
            font-style: italic;
            text-align: center;
            margin-top: 50px;
          }
          
          /* Print styles */
          @media print {
            body {
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
            
            .soap-grid {
              height: calc(100vh - 120px);
            }
            
            .soap-section {
              break-inside: avoid;
            }
          }
          
          @page {
            size: A4;
            margin: 1cm;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>تقرير الملاحظة الطبية SOAP</h1>
          <p style="font-size: 12px; color: #666;">تاريخ الإنشاء: ${new Date().toLocaleDateString('ar-SA')}</p>
        </div>
        
        <div class="soap-grid">
          <!-- Subjective Section (Top Left) -->
          <div class="soap-section">
            <h2>القسم الذاتي - Subjective</h2>
            <div class="section-content">
              ${soapNote.subjective && Object.keys(soapNote.subjective).length > 0 
                ? Object.entries(soapNote.subjective)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">لا توجد بيانات متاحة</div>'
              }
            </div>
          </div>
          
          <!-- Objective Section (Top Right) -->
          <div class="soap-section">
            <h2>القسم الموضوعي - Objective</h2>
            <div class="section-content">
              ${soapNote.objective && Object.keys(soapNote.objective).length > 0 
                ? Object.entries(soapNote.objective)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">لا توجد بيانات متاحة</div>'
              }
            </div>
          </div>
          
          <!-- Assessment Section (Bottom Left) -->
          <div class="soap-section">
            <h2>التقييم - Assessment</h2>
            <div class="section-content">
              ${soapNote.assessment && Object.keys(soapNote.assessment).length > 0 
                ? Object.entries(soapNote.assessment)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">لا توجد بيانات متاحة</div>'
              }
            </div>
          </div>
          
          <!-- Plan Section (Bottom Right) -->
          <div class="soap-section">
            <h2>الخطة - Plan</h2>
            <div class="section-content">
              ${soapNote.plan && Object.keys(soapNote.plan).length > 0 
                ? Object.entries(soapNote.plan)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">لا توجد بيانات متاحة</div>'
              }
            </div>
          </div>
        </div>
        
        <script>
          // Auto-print when page loads
          window.onload = function() {
            setTimeout(() => {
              window.print();
            }, 1000);
          };
          
          // Close window after printing
          window.onafterprint = function() {
            setTimeout(() => {
              window.close();
            }, 1000);
          };
        </script>
      </body>
      </html>
    `;
    
    // Open in new window for printing
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }
  
  // Alternative function for generating English PDF with same layout
  export function generateEnglishPDF(soapNote) {
    const formatFieldName = (key) => {
      return key.replace(/_/g, ' ')
               .split(' ')
               .map(word => word.charAt(0).toUpperCase() + word.slice(1))
               .join(' ');
    };
  
    const htmlContent = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SOAP Note Report</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          
          body { 
            font-family: 'Segoe UI', Tahoma, Arial, sans-serif; 
            padding: 20px;
            line-height: 1.4;
            font-size: 11px;
            background: white;
          }
          
          .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
          }
          
          .header h1 {
            font-size: 20px;
            color: #333;
            margin-bottom: 5px;
          }
          
          .soap-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 2px;
            height: calc(100vh - 150px);
            border: 2px solid #000;
          }
          
          .soap-section {
            border: 1px solid #000;
            padding: 15px;
            overflow: hidden;
          }
          
          .soap-section h2 {
            font-size: 14px;
            color: #000;
            margin-bottom: 15px;
            text-align: center;
            font-weight: bold;
            border-bottom: 1px solid #666;
            padding-bottom: 8px;
          }
          
          .section-content {
            height: calc(100% - 45px);
            overflow: hidden;
          }
          
          .field-item {
            margin-bottom: 12px;
            line-height: 1.3;
          }
          
          .field-label {
            font-weight: bold;
            color: #333;
            font-size: 10px;
            margin-bottom: 3px;
            display: block;
          }
          
          .field-value {
            color: #000;
            font-size: 11px;
            margin-left: 10px;
            word-wrap: break-word;
            overflow-wrap: break-word;
          }
          
          .no-data {
            color: #666;
            font-style: italic;
            text-align: center;
            margin-top: 50px;
          }
          
          @media print {
            body {
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
            
            .soap-grid {
              height: calc(100vh - 120px);
            }
            
            .soap-section {
              break-inside: avoid;
            }
          }
          
          @page {
            size: A4;
            margin: 1cm;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>SOAP Note Template</h1>
          <p style="font-size: 12px; color: #666;">Generated on: ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div class="soap-grid">
          <!-- Subjective Section -->
          <div class="soap-section">
            <h2>Subjective Section</h2>
            <div class="section-content">
              ${soapNote.subjective && Object.keys(soapNote.subjective).length > 0 
                ? Object.entries(soapNote.subjective)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">No data available</div>'
              }
            </div>
          </div>
          
          <!-- Objective Section -->
          <div class="soap-section">
            <h2>Objective Section</h2>
            <div class="section-content">
              ${soapNote.objective && Object.keys(soapNote.objective).length > 0 
                ? Object.entries(soapNote.objective)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">No data available</div>'
              }
            </div>
          </div>
          
          <!-- Assessment Section -->
          <div class="soap-section">
            <h2>Assessment Section</h2>
            <div class="section-content">
              ${soapNote.assessment && Object.keys(soapNote.assessment).length > 0 
                ? Object.entries(soapNote.assessment)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">No data available</div>'
              }
            </div>
          </div>
          
          <!-- Plan Section -->
          <div class="soap-section">
            <h2>Plan Section</h2>
            <div class="section-content">
              ${soapNote.plan && Object.keys(soapNote.plan).length > 0 
                ? Object.entries(soapNote.plan)
                    .filter(([key, value]) => value && value.trim())
                    .map(([key, value]) => `
                      <div class="field-item">
                        <span class="field-label">${formatFieldName(key)}:</span>
                        <div class="field-value">${value}</div>
                      </div>
                    `).join('')
                : '<div class="no-data">No data available</div>'
              }
            </div>
          </div>
        </div>
        
        <script>
          window.onload = function() {
            setTimeout(() => {
              window.print();
            }, 1000);
          };
          
          window.onafterprint = function() {
            setTimeout(() => {
              window.close();
            }, 1000);
          };
        </script>
      </body>
      </html>
    `;
    
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }