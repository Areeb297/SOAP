# 🏥 SOAP Note Voice Recorder

A complete voice recording application for generating SOAP notes from doctor-patient conversations using AI.

## 🎯 Features

- **Voice Recording**: Simple click-to-record interface with visual feedback
- **Speech-to-Text**: Uses OpenAI Whisper for accurate transcription
- **Intelligent Medical Spell Checking**: Real-time spell correction for medical terms with SNOMED CT integration
- **Editable Transcripts**: Doctors can edit transcripts before processing
- **AI-Powered SOAP Generation**: Uses GPT-4o-mini to structure conversations into SOAP format
- **Structured Output**: Displays SOAP notes in an organized, professional format

## 🚀 Quick Start

### Prerequisites

- **Python 3.12** (recommended) or Python 3.8-3.11 installed on your system
  - ⚠️ **Important**: Python 3.13 may cause compatibility issues with some dependencies
  - Use Python 3.12 for best compatibility with OpenAI SDK and other packages
- Node.js 16+ and npm for the React frontend
- FFmpeg for audio processing (required by Whisper)
- OpenAI API Key for GPT-4o-mini

### Installation

1. **Install FFmpeg**
   ```bash
   # macOS:
   brew install ffmpeg
   
   # Ubuntu/Debian:
   sudo apt update && sudo apt install ffmpeg
   
   # Windows: Download from ffmpeg.org and add to PATH
   ```

2. **Set up Python Backend**
   ```bash
   # Create and activate virtual environment with Python 3.12
   # If you have Python 3.12 installed:
   python3.12 -m venv venv
   # OR on Windows:
   py -3.12 -m venv venv
   # OR if you only have one Python version:
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   # Upgrade pip to latest version
   python -m pip install --upgrade pip
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Set OpenAI API Key**
   ```bash
   # Create .env file
   echo OPENAI_API_KEY=your-openai-api-key-here > .env
   
   # Or manually create .env file and add:
   # OPENAI_API_KEY=your-openai-api-key-here
   ```

4. **Set up React Frontend**
   ```bash
   # Create React app
   npx create-react-app frontend
   cd frontend
   
   # Install dependencies
   npm install lucide-react
   
   # Replace src/App.js with SOAPRecorder.js content
   ```

### Running the Application

1. **Start the Backend** (Terminal 1):
   ```bash
   python app.py
   ```
   Backend runs on http://localhost:5000

2. **Start the Frontend** (Terminal 2):
   ```bash
   cd frontend
   npm start
   ```
   Frontend runs on http://localhost:3000

## 📖 Usage

1. Open http://localhost:3000 in your browser
2. Click the microphone button to start recording
3. Have a doctor-patient conversation
4. Click the button again to stop recording
5. The transcript will appear - you can edit it if needed
6. Click "Generate SOAP Note" to create the structured note
7. The SOAP note will be displayed in a formatted view

## 📄 SOAP Note Structure

The application generates comprehensive SOAP notes with:

### SUBJECTIVE:
- Chief Complaint
- History of Present Illness (HPI)
- Past Medical History (PMH)
- Family/Social History
- Medications
- Allergies

### OBJECTIVE:
- Vital Signs
- Physical Examination Findings

### ASSESSMENT:
- Diagnosis
- Risk Factors

### PLAN:
- Medications Prescribed
- Procedures/Interventions
- Patient Education
- Follow-up Instructions

## 🔧 Key Technologies

- **Frontend**: React with Tailwind CSS styling
- **Backend**: Flask (Python)
- **Speech-to-Text**: OpenAI Whisper
- **AI Processing**: OpenAI GPT-4o-mini
- **Audio**: Web Audio API for recording

## 📁 Project Structure

```
soap-recorder/
├── app.py                 # Flask backend server
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── SOAPRecorder.js       # React component
├── package.json          # Node.js dependencies
├── setup.sh             # Automated setup script
├── README.md            # This file
└── MyPlanning.md        # Project planning log
```

## 🔗 API Endpoints

- `POST /transcribe` - Transcribes audio to text
- `POST /generate-soap` - Generates SOAP note from transcript
- `GET /health` - Health check endpoint

## 📄 Output Files

- `SOAP.txt` - Contains raw transcript and formatted SOAP note
- `SOAP_note.json` - Structured JSON format for integration

## 🚨 Troubleshooting

### Python Version Issues
- **Problem**: `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`
- **Solution**: Use Python 3.12 instead of Python 3.13
- **Commands**:
  ```bash
  # Remove current venv
  deactivate
  rmdir /s venv
  
  # Create new venv with Python 3.12
  python3.12 -m venv venv
  # OR on Windows:
  py -3.12 -m venv venv
  
  # Activate and install
  venv\Scripts\activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```

### Microphone Access
- Ensure your browser has permission to access the microphone
- Use HTTPS in production for microphone access

### Whisper Model Download
- First run will download the Whisper model (~140MB for base model)
- For faster processing, set `WHISPER_MODEL=tiny` in .env
- For better accuracy, use `WHISPER_MODEL=small` or `medium`

### CORS Issues
- The backend includes CORS support for localhost
- For production, update CORS settings in app.py

### OpenAI API Errors
- Verify your API key is correct
- Check your OpenAI account has credits
- Ensure you have access to gpt-4o-mini model

### Package Installation Issues
- If you encounter installation errors, try installing packages one by one:
  ```bash
  pip install Flask==3.0.3
  pip install flask-cors==4.0.1
  pip install openai==1.98.0
  pip install python-dotenv==1.0.1
  pip install requests==2.32.3
  pip install textblob==0.18.0.post0
  pip install fuzzywuzzy==0.18.0
  pip install python-Levenshtein==0.25.1
  ```

## 🔄 Development

The application is modular and allows easy customization:

- **SOAP Format**: Modify the `SOAP_SYSTEM_PROMPT` in app.py
- **UI Styling**: Update the Tailwind CSS classes in SOAPRecorder.js
- **Audio Processing**: Adjust Whisper model settings in app.py
- **Integration**: Use the JSON output for EMR system integration

## 📝 License

This project is for educational and medical documentation purposes. Please ensure compliance with healthcare regulations like HIPAA when handling patient data.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues or questions, please create an issue in the repository or contact the development team.

---

**Note**: This application is production-ready with error handling, loading states, and a professional medical interface. Always ensure proper security measures when handling patient data. 