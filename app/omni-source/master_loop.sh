#!/bin/bash

# Force the cron environment to see your installed software (Python, Ollama)
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH

# Define strict absolute paths
STUDIO_DIR="$HOME/Omni-Studio"
LOGFILE="$STUDIO_DIR/logs/master_engine.log"

cd "$STUDIO_DIR" || exit

echo "===================================================" >> "$LOGFILE"
echo "[$(date)] 🔄 MASTER LOOP CYCLE INITIATED" >> "$LOGFILE"

# 1. Hunt for new leads
/usr/bin/env python3 "$STUDIO_DIR/integrations/scraper.py" >> "$LOGFILE" 2>&1

# 2. Reconcile incoming cash & issue gate codes
/usr/bin/env python3 "$STUDIO_DIR/scripts/income_watchdog.py" >> "$LOGFILE" 2>&1

# 3. Autonomously reply to artist inquiries
/usr/bin/env python3 "$STUDIO_DIR/agents/inbound_agent.py" >> "$LOGFILE" 2>&1

# 4. Blast out newly generated pitches
/usr/bin/env python3 "$STUDIO_DIR/integrations/send_ar_pitches.py" >> "$LOGFILE" 2>&1

echo "[$(date)] ✅ CYCLE COMPLETE. SLEEPING FOR 15 MIN..." >> "$LOGFILE"
echo "===================================================" >> "$LOGFILE"
