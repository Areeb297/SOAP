#!/bin/bash
# setup.sh - Quick setup script for SOAP Note Voice Recorder

echo "🏥 SOAP Note Voice Recorder Setup"
echo "================================"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js installation
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

# Check FFmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed. Installing instructions:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    echo "   Windows: Download from ffmpeg.org"
    read -p "Press Enter to continue after installing FFmpeg..."
fi

# Backend setup
echo "📦 Setting up Python backend..."
python3 -m venv venv
source venv/bin/activate 2>/dev/null || venv\Scripts\activate

echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env 2>/dev/null || echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "⚠️  Please edit .env and add your OpenAI API key"
fi

# Frontend setup
echo "📦 Setting up React frontend..."
if [ ! -d "frontend" ]; then
    mkdir frontend
    cd frontend
    npm init -y
    npm install react react-dom react-scripts lucide-react
    cd ..
fi

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "1. Terminal 1: python app.py"
echo "2. Terminal 2: cd frontend && npm start"
echo ""
echo "⚠️  Don't forget to add your OpenAI API key to the .env file!" 