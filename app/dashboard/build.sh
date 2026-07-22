#!/bin/bash
# Build Omni-Studio as macOS app
# Usage: ./build.sh

set -e

echo "Building Omni-Studio.app..."

# Install pyinstaller if needed
pip3 install pyinstaller 2>/dev/null || pip install pyinstaller

# Build
cd "$(dirname "$0")"

pyinstaller \
    --name "Omni-Studio" \
    --windowed \
    --onedir \
    --icon icon.icns \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --add-data "data:data" \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import aiosqlite \
    --hidden-import apscheduler \
    --hidden-import httpx \
    --hidden-import mutagen \
    --hidden-import watchdog \
    launcher.py

echo ""
echo "Build complete!"
echo "App: dist/Omni-Studio/Omni-Studio"
echo ""
echo "To create .app bundle:"
echo "  mkdir -p 'dist/Omni-Studio.app/Contents/MacOS'"
echo "  mkdir -p 'dist/Omni-Studio.app/Contents/Resources'"
echo "  cp dist/Omni-Studio/Omni-Studio dist/Omni-Studio.app/Contents/MacOS/"
echo "  cp Info.plist dist/Omni-Studio.app/Contents/"
