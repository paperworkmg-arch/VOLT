#!/bin/bash
# Freelance Bot - Desktop Launcher
# Double-click to check for new freelance jobs

cd "$(dirname "$0")/app/omni-source"

echo "Freelance Bot - Checking for new jobs..."
echo ""

# Check for new jobs and send notifications
python3 scripts/freelance_bot.py check

echo ""
echo "Done! Check your notifications."
echo ""
echo "Other commands:"
echo "  python3 scripts/freelance_bot.py list     - List all jobs"
echo "  python3 scripts/freelance_bot.py approve <file> - Approve a job"
echo "  python3 scripts/freelance_bot.py reject <file>  - Reject a job"
echo ""
read -p "Press Enter to exit..."
