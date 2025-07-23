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