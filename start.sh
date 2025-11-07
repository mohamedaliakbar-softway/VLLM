#!/bin/bash

# Video Shorts Generator - Startup Script

echo "🚀 Starting Video Shorts Generator API..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    
    cat > .env << EOF
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Video Processing Configuration
MAX_VIDEO_DURATION=1800
MIN_VIDEO_DURATION=900
SHORT_DURATION_MIN=15
SHORT_DURATION_MAX=30
MAX_HIGHLIGHTS=3

# Storage Configuration
TEMP_DIR=./temp
OUTPUT_DIR=./output
EOF
    
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env and add your GEMINI_API_KEY"
    echo ""
    read -p "Press enter to continue after adding your API key..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create directories
mkdir -p temp output

# Start the server
echo ""
echo "🌐 Starting API server at http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
python main.py

