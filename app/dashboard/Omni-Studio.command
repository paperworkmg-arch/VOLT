#!/bin/bash
# Omni-Studio Launcher (no-build version)
# Double-click to run

cd "$(dirname "$0")"

echo "Starting Omni-Studio..."
echo ""

# Create virtual environment if missing
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
python3 -c "import fastapi" 2>/dev/null || {
  echo "Installing dependencies..."
  pip install --quiet uvicorn fastapi watchfiles
}

# Run the app
python3 launcher.py
