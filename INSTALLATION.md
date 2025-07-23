# 🏥 SOAP Note Voice Recorder - Installation Guide

## Prerequisites

- Python 3.8+ installed on your system
- Node.js 16+ and npm for the React frontend
- FFmpeg for audio processing (required by Whisper)
- OpenAI API Key for GPT-4o-mini

## Installation Steps

### 1. Install FFmpeg

**On macOS:**
```bash
brew install ffmpeg
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**On Windows:**
Download from [ffmpeg.org](https://ffmpeg.org) and add to PATH.

### 2. Set up Python Backend

```bash
# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Set OpenAI API Key

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your OpenAI API key
OPENAI_API_KEY=your-api-key-here
```

Or set it as an environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Set up React Frontend

```bash
# Create a new React app
npx create-react-app frontend
cd frontend

# Install required dependencies
npm install lucide-react

# Replace src/App.js with the provided SOAPRecorder.js component
```

## Running the Application

### 1. Start the Python Backend

```bash
# Make sure virtual environment is activated
python app.py
```

The backend will start on http://localhost:5000

### 2. Start the React Frontend

In a new terminal:
```bash
cd frontend
npm start
```

The frontend will start on http://localhost:3000

## Complete Installation Commands

```bash
# 1. Install system dependencies
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# 2. Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install all Python packages in one command
pip install flask==3.0.0 flask-cors==4.0.0 openai-whisper==20231117 ffmpeg-python==0.2.0 openai==0.28.1 numpy==1.26.2 scipy==1.11.4 python-dotenv==1.0.0

# 4. Create React frontend
npx create-react-app frontend
cd frontend
npm install lucide-react

# 5. Set up environment variables
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env

# 6. Run the backend (in project root)
python app.py

# 7. Run the frontend (in frontend directory)
npm start
```

## Usage

1. Open http://localhost:3000 in your browser
2. Click the microphone button to start recording
3. Have a doctor-patient conversation
4. Click the button again to stop recording
5. The transcript will appear - you can edit it if needed
6. Click "Generate SOAP Note" to create the structured note
7. The SOAP note will be displayed in a formatted view

## File Outputs

- `SOAP.txt` - Contains the raw transcript and generated SOAP note
- `SOAP_note.json` - Contains the structured SOAP note in JSON format

## API Endpoints

- `POST /transcribe` - Transcribes audio to text
- `POST /generate-soap` - Generates SOAP note from transcript
- `GET /health` - Health check endpoint

## Troubleshooting

### Microphone Access
- Ensure your browser has permission to access the microphone
- Use HTTPS in production for microphone access

### Whisper Model Download
- First run will download the Whisper model (~140MB for base model)
- For faster processing, use "tiny" model instead of "base"
- For better accuracy, use "small" or "medium" model

### CORS Issues
- The backend includes CORS support for localhost
- For production, update CORS settings in app.py

### OpenAI API Errors
- Verify your API key is correct
- Check your OpenAI account has credits
- Ensure you have access to gpt-4o-mini model 