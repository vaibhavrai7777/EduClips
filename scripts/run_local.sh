#!/bin/bash
# ===================================
# EduClips — Local Development Runner
# ===================================

set -e

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Install it:"
    echo "   Mac:   brew install ffmpeg"
    echo "   Linux: sudo apt-get install ffmpeg"
    echo "   Win:   https://ffmpeg.org/download.html"
    exit 1
fi

echo "✅ FFmpeg found: $(ffmpeg -version 2>&1 | head -1)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# Create and activate virtual environment
cd backend

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Load .env
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
    echo "✅ Loaded .env"
else
    echo "⚠️  No .env file found. Copy .env.example to .env and fill in your API key."
fi

# Start server
echo ""
echo "🚀 Starting EduClips server at http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
