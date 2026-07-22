#!/bin/bash
# Build Volt Records Dashboard
# Run this after installing node/npm

set -e

echo "Building Volt Records Dashboard..."

cd "$(dirname "$0")"

# Install dependencies
npm install

# Build for production
npm run build

echo ""
echo "Build complete!"
echo "Dashboard available at: /volt"
echo ""
echo "To serve from Omni-Studio:"
echo "  cd ../dashboard && python3 omni.py"
echo "  Then visit: http://127.0.0.1:8500/volt"
