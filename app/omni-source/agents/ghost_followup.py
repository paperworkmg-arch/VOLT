import os
import re
import subprocess
from datetime import datetime, timedelta

# --- CONFIGURATION ---
PITCH_DIR = os.path.expanduser("~/Omni-Studio/Outbound_Pitches")
CLOSED_DIR = os.path.expanduser("~/Omni-Studio/Closed_Deals")
# Set to 0.01 for testing (roughly 30 seconds) or 48 for real production use
HOURS_THRESHOLD = 48

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 👻 Ghost Follow-Up Engine checking outstanding pitches...")

if not os.path.exists(PITCH_DIR):
    print("No pitch directory found. Run your watchdog first.")
    exit()

# Get a list of closed artists so we NEVER nudge someone who already paid
closed_artists = set()
if os.path.exists(CLOSED_DIR):
    closed_artists = {f.replace(".txt", "").lower() for f in os.listdir(CLOSED_DIR)}

for filename in os.listdir(PITCH_DIR):
    if filename.endswith("_pitch.txt") and not filename.startswith("."):
        artist_name = filename.replace("_pitch.txt", "")
        
        # Guardrails: Skip if they already locked in
        if artist_name.lower() in closed_artists:
            continue
            
        file_path = os.path.join(PITCH_DIR, filename)
        
        # Check file modified time
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        time_elapsed = datetime.now() - mtime
        
        if time_elapsed > timedelta(hours=HOURS_THRESHOLD):
            # Read the original pitch to maintain context
            with open(file_path, "r", encoding="utf-8") as f:
                original_pitch = f.read()
            
            # Skip if we already wrote a follow-up for this file
            if "FOLLOW-UP NUDGE" in original_pitch:
                continue
                
            print(f"⚠️  [{artist_name}] hasn't replied. Engineering a soft nudge...")
            
            prompt = f"""
            You are Mykel T. Brooks, a sharp, professional Atlanta studio owner and producer. 
            You are following up with an artist who hasn't locked in their booking yet.
            
            ORIGINAL PITCH SENT:
            {original_pitch}
            
            DIRECTIONS:
            Write a quick, casual, non-spammy follow-up text/DM (1-2 sentences max). 
            Sound like a busy professional who has other artists waiting to book the same room, but wants to give them first dibs. 
            Mention his project link http://sqtheafterparty.base44.app/ naturally if they need inspiration.
            Use Atlanta music industry slang (e.g., "lock in", "secure the slot", "vibes").
            
            Format your output EXACTLY like this:
            FOLLOW-UP NUDGE:
            [Your 1-2 sentence text here]
            """
            
            # Call Ollama
            cmd = ["ollama", "run", "qwen3:14b", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            # Append the follow-up directly to their pitch file so you have a single thread history
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n\n=========================================\n")
                f.write(result.stdout.strip())
                
            print(f"   🔥 Saved custom nudge to {filename}")

