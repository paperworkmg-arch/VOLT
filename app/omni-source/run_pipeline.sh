echo "Running the pipeline..."
python3 ~/Omni-Studio/integrations/scraper.py
python3 ~/Omni-Studio/integrations/fetch_emails.py
sh ~/Omni-Studio/watchdog.sh
echo "Pipeline completed. Results in ~/Omni-Studio/data/"