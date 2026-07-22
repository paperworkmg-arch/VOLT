import os
import time
import subprocess
import logging
from datetime import datetime

# Setup Logging
log_dir = os.path.expanduser("~/Omni-Studio/logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'daemon.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Volt-Orchestrator')

# Load API keys from .env so child scripts (Serper, Gemini, LLM providers) inherit them
env_path = os.path.expanduser("~/Omni-Studio/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# The scripts we built in previous steps
# name -> (script path, run every Nth cycle; one cycle = 15 minutes)
SCRIPTS = {
    'Scraper': ('integrations/scraper.py', 1),
    'Outbound Pitcher': ('integrations/send_ar_pitches.py', 1),
    'Inbound AI Agent': ('agents/inbound_agent.py', 1),
    'Income Watchdog': ('scripts/income_watchdog.py', 1),
    'Contact Enricher': ('agents/contact_enricher.py', 1),
    'Send Queue': ('agents/send_queue.py', 1),
    'Approved Sender': ('agents/approved_sender.py', 1),
    'Music Library Aggregator': ('agents/music_library_aggregator.py', 96),  # ~once a day
}

def run_script(name, filename):
    script_path = os.path.expanduser(f"~/Omni-Studio/{filename}")
    venv_python = os.path.expanduser("~/Omni-Studio/.venv/bin/python3")
    
    if not os.path.exists(script_path):
        logger.warning(f"⚠️  Skipping {name}: {filename} not found.")
        return

    try:
        logger.info(f"▶️ Running {name}...")
        result = subprocess.run([venv_python, script_path], capture_output=True, text=True)
        
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip(): logger.info(f"  ↳ {line.strip()}")
                
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip(): logger.error(f"  ↳ {line.strip()}")
                
        logger.info(f"✅ {name} Cycle Complete.")
    except Exception as e:
        logger.error(f"❌ Failed to run {name}: {str(e)}")

if __name__ == "__main__":
    logger.info("===============================================")
    logger.info("🔥 OMNI-STUDIO ELITE ORCHESTRATOR LIVE")
    logger.info("===============================================")
    
    cycle = 0
    while True:
        try:
            cycle += 1
            logger.info("🔄 Initiating Master Cycle...")

            for name, (file, every) in SCRIPTS.items():
                if (cycle - 1) % every == 0:
                    run_script(name, file)
                
            logger.info("💤 Master Cycle Complete. Sleeping for 15 minutes...")
            time.sleep(900)
            
        except KeyboardInterrupt:
            logger.info("🛑 Orchestrator shutting down.")
            break
        except Exception as e:
            logger.critical(f"💀 CRITICAL ERROR: {str(e)}")
            time.sleep(60)
