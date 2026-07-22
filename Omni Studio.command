#!/bin/bash
# Omni Studio - Desktop Launcher
# Double-click this file to launch Omni Studio

cd "$(dirname "$0")"

echo "Starting Omni Studio..."
echo ""

# Check if Pinokio is installed
if command -v pinokio &> /dev/null; then
    echo "Launching via Pinokio..."
    pinokio start omni-studio
else
    echo "Pinokio not found. Starting manually..."
    
    # Start the dashboard
    cd app/dashboard
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    echo "Starting Omni Studio on http://127.0.0.1:8500"
    python omni.py &
    
    # Open browser after delay
    sleep 3
    open http://127.0.0.1:8500
fi
