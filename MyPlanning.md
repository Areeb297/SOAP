# SOAP Note Voice Recorder - Setup Planning

## Current Status: Setup Phase

### Prerequisites Checklist
- [ ] Python 3.8+ installed and accessible
- [ ] Node.js 16+ and npm installed
- [ ] FFmpeg installed and in PATH
- [ ] OpenAI API key obtained

### Installation Tasks

#### 1. System Prerequisites
- [ ] Verify Python version: `python --version`
- [ ] Verify Node.js version: `node --version`
- [ ] Verify npm version: `npm --version`
- [ ] Check if FFmpeg is installed: `ffmpeg -version`

#### 2. FFmpeg Installation (Windows)
- [ ] Download FFmpeg from https://ffmpeg.org/download.html
- [ ] Extract to C:\ffmpeg
- [ ] Add C:\ffmpeg\bin to system PATH
- [ ] Verify installation with `ffmpeg -version`

#### 3. Python Backend Setup
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment: `venv\Scripts\activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Create .env file with OpenAI API key
- [ ] Test backend startup: `python app.py`

#### 4. React Frontend Setup
- [ ] Navigate to frontend directory: `cd soap-recorder-frontend`
- [ ] Install dependencies: `npm install`
- [ ] Install additional packages: `npm install lucide-react`
- [ ] Test frontend startup: `npm start`

#### 5. Configuration
- [ ] Create .env file in root directory
- [ ] Add OpenAI API key to .env
- [ ] Verify CORS settings in app.py
- [ ] Check microphone permissions in browser

#### 6. Testing
- [ ] Test audio recording functionality
- [ ] Test transcription service
- [ ] Test SOAP note generation
- [ ] Verify file outputs (SOAP.txt, SOAP_note.json)

#### 7. Troubleshooting
- [ ] Document any issues encountered
- [ ] Test with different Whisper models (tiny/base/small)
- [ ] Verify HTTPS requirements for production
- [ ] Check API rate limits and credits

## Completed Tasks
- [x] Initial project structure reviewed
- [x] Setup guide documentation provided 
- [x] Updated backend to always transcribe audio in English (set language='en' in Whisper transcribe calls) 
- [ ] Update backend to always include all SOAP categories (fill missing with 'None mentioned')
- [ ] Add download buttons (PDF and TXT) to frontend SOAP note display 
- [ ] Improve PDF export formatting to match 2x2 SOAP note template layout 
- [ ] Fix PDF export text wrapping and spacing in each cell
- [ ] Update backend prompt to encourage more detailed SOAP notes 
- [ ] Add language selector (English/Arabic) to frontend
- [ ] Use Hugging Face transformers pipeline for Arabic transcription in backend
- [ ] Use Whisper for English transcription in backend
- [ ] Update backend requirements for transformers and torch 

## New Task: UI Structure Changes for SOAP Note Sections

### Goal
Implement UI changes to improve SOAP note section structure and styling.

### Changes Required
1. **Add section names as comments in each div**
   - Add `<!-- SUBJECTIVE Section -->` before subjective section div
   - Add `<!-- OBJECTIVE Section -->` before objective section div  
   - Add `<!-- ASSESSMENT Section -->` before assessment section div
   - Add `<!-- PLAN Section -->` before plan section div

2. **Add CSS classes to section divs**
   - Add `subjective` class to subjective section div
   - Add `objective` class to objective section div
   - Add `assessment` class to assessment section div
   - Add `plan` class to plan section div

3. **Add wrapper div for SOAP data**
   - Add `<div class="soap_data">` before the first SOAP section
   - Close this div before the Agreement Section

### Implementation Steps
- [x] Update SOAPSection component to include section-specific CSS classes
- [x] Add HTML comments for each section
- [x] Wrap all SOAP sections in a `soap_data` div
- [x] Test the changes to ensure proper styling and structure
- [x] Mark task complete after implementation

### Task Status: ✅ COMPLETED
The UI structure changes have been successfully implemented:
- Added section-specific CSS classes (`subjective`, `objective`, `assessment`, `plan`) to each SOAP section div
- Added HTML comments (`<!-- SUBJECTIVE Section -->`, etc.) before each section
- Wrapped all SOAP sections in a `soap_data` div container
- The changes maintain existing functionality while improving code structure and styling capabilities

## New Task: Add Username/Password Authentication After User Agreement

### Goal
Implement an additional security layer by requiring username and password input after the user agreement checkbox before allowing PDF/TXT downloads.

### Changes Required
1. **Add state management for authentication**
   - Add state for username and password input
   - Add state to track if authentication is completed
   - Add state to show/hide authentication form

2. **Create authentication form component**
   - Username input field
   - Password input field (with proper type="password")
   - Confirm/Save button
   - Cancel button to go back

3. **Update download button logic**
   - Change condition from `userAgreement` to `userAgreement && isAuthenticated`
   - Show authentication form when checkbox is checked
   - Hide authentication form when authentication is completed

4. **Improve user experience**
   - Clear form when user unchecks agreement
   - Add proper validation for username/password fields
   - Add loading state during authentication process

### Implementation Steps
- [x] Add new state variables for authentication
- [x] Create authentication form component
- [x] Update user agreement checkbox logic
- [x] Update download button conditions
- [x] Add form validation and error handling
- [x] Test the complete authentication flow
- [x] Mark task complete after implementation

### Task Status: ✅ COMPLETED
The authentication feature has been successfully implemented:
- Added state management for username, password, authentication status, and form visibility
- Created a clean authentication form with proper validation
- Updated user agreement checkbox to show authentication form when checked
- Modified download buttons to require both agreement and authentication
- Added proper error handling and user feedback
- Implemented cancel functionality to reset the entire flow
- Added success message when authentication is completed

# Task: Integrate Arabic Font for PDF Export (jsPDF)

## Goal
Ensure that Arabic text in generated PDFs is displayed correctly for all users, with no extra downloads or setup required by end users.

## Steps

### 1. Convert the TTF Font to jsPDF Format
- Go to the [jsPDF font converter tool](https://simonbengtsson.github.io/jsPDF-AutoTable/tools/font-converter.html).
- Upload your `NotoNaskhArabic-Regular.ttf` file (found in `soap-recorder-frontend/public/fonts/`).
- Set the font name to `NotoNaskhArabic` (or keep the default if you prefer).
- Click "Download js-file" to get the converted font file (e.g., `NotoNaskhArabic-Regular.js`).

### 2. Add the Converted Font File to Your Project
- Place the downloaded `NotoNaskhArabic-Regular.js` file in your project, e.g., in `soap-recorder-frontend/public/fonts/` or `soap-recorder-frontend/src/fonts/`.

### 3. Import the Font in Your Code
- In your `SOAPRecorder.js` (or wherever you generate the PDF), add:
  ```js
  import '../public/fonts/NotoNaskhArabic-Regular.js';
  // or
  // import '../src/fonts/NotoNaskhArabic-Regular.js';
  ```
  (Adjust the path as needed based on where you placed the file.)

### 4. Update PDF Generation Logic
- Remove any dynamic font loading logic (e.g., `addFileToVFS`, `addFont`, and base64 font loading for NotoNaskhArabic).
- Before rendering Arabic text, set the font:
  ```js
  doc.setFont('NotoNaskhArabic', 'normal');
  ```
- Keep your logic for detecting Arabic and switching fonts as needed.

### 5. Test PDF Export
- Generate a SOAP note in Arabic and download as PDF.
- Open the PDF and verify that Arabic text displays correctly.
- Test on a different device/browser to confirm it works for all users.

---

## Completion Checklist
- [ ] Font converted and added to project
- [ ] Font imported in code
- [ ] PDF generation logic updated
- [ ] PDF export tested and verified

---

**Once these steps are complete, all users will see correct Arabic text in PDFs, with no extra setup required!** 

## Enhanced Follow-up and Patient Education (Completed)
- [x] Update English SOAP prompt with diagnosis-specific follow-up instructions
- [x] Update Arabic SOAP prompt with diagnosis-specific follow-up instructions
- [x] Enhance patient education to be more comprehensive and diagnosis-specific
- [x] Include emergency return criteria and specialist referrals
- [x] Mark task complete after prompt improvements

## UI/UX Improvements (Completed)
- [x] Center data alignment in all SOAP note sections
- [x] Make metadata section (patient ID, date, provider, patient name, age) editable
- [x] Improve visual consistency across all sections
- [x] Enhance user experience with better layout
- [x] Mark task complete after UI improvements

## Final Quality Improvements (Completed)
- [x] Implement cleanSOAPNote function in frontend
- [x] Add post-processing logic to backend
- [x] Update SOAPSection component for better rendering of arrays and objects
- [x] Ensure consistent display of nested data structures
- [x] Improve metadata handling and display
- [x] Mark task complete after final improvements

---

**All planned improvements have been successfully implemented!** 🎉