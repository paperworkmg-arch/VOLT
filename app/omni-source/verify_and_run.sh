echo "Checking for required files..."
if [ -f ~/Omni-Studio/integrations/scraper.py ] && [ -f ~/Omni-Studio/integrations/fetch_emails.py ] && [ -f ~/Omni-Studio/watchdog.sh ]; then
    echo "All files present. Running pipeline..."
    sh ~/Omni-Studio/run_pipeline.sh
else
    echo "Missing files. Please ensure all components are in place before running."
fi