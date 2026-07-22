#!/usr/bin/env python3
"""
Omni-Studio Launcher
Entry point for packaged app. Handles imports and starts the server.
"""
import os, sys, webbrowser, threading, time
from pathlib import Path

# Ensure we're in the right directory
APP_DIR = Path(__file__).parent
os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))

HOST = "127.0.0.1"
PORT = 8500

def open_browser():
    """Wait for server then open browser."""
    time.sleep(2)
    webbrowser.open(f"http://{HOST}:{PORT}")

def main():
    # Start browser opener in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Import and run the app
    import uvicorn
    print(f"\n  Omni-Studio Dashboard")
    print(f"  http://{HOST}:{PORT}\n")
    uvicorn.run("omni:app", host=HOST, port=PORT, reload=False)

if __name__ == "__main__":
    main()
