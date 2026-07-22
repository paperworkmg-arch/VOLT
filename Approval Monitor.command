#!/bin/bash
# Approval Monitor - Desktop Launcher
# Double-click to check pending approvals

cd "$(dirname "$0")/app/omni-source"

echo "Approval Monitor - Checking for pending approvals..."
echo ""

# Check for pending approvals and send notifications
python3 scripts/approval_monitor.py

echo ""
echo "Done! Check your notifications."
echo ""
read -p "Press Enter to exit..."
