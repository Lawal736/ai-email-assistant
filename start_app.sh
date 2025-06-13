#!/bin/bash

# AI Email Assistant Startup Script

echo "🚀 Starting AI Email Assistant..."

# Kill any existing processes on port 5001
echo "🧹 Cleaning up port 5001..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true

# Kill any existing Python/Flask processes
echo "🧹 Cleaning up Python processes..."
pkill -f "python3 app.py" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Check if credentials.json exists
if [ ! -f "credentials.json" ]; then
    echo "❌ Error: credentials.json not found!"
    echo "Please download your Google Cloud Console credentials and place them in the project directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Make sure you have set up your OpenAI API key in the .env file."
fi

# Start the Flask app
echo "🌟 Starting Flask app on http://localhost:5001"
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py 