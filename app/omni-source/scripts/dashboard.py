import os
import re
from datetime import datetime

# --- CONFIGURATION & PATHS ---
STUDIO_DIR = os.path.expanduser("~/Omni-Studio")
LEADS_DIR = os.path.join(STUDIO_DIR, "Incoming_Leads")
CLOSED_DIR = os.path.join(STUDIO_DIR, "Closed_Deals")
PITCH_DIR = os.path.join(STUDIO_DIR, "Outbound_Pitches")
PR_DIR = os.path.join(STUDIO_DIR, "Press_Pitches")

def count_files(directory, extension=None):
    if not os.path.exists(directory):
        return 0
    files = os.listdir(directory)
    if extension:
        files = [f for f in files if f.endswith(extension)]
    return len([f for f in files if not f.startswith('.')])

# Get pipeline counts
leads_count = count_files(LEADS_DIR)
closed_count = count_files(CLOSED_DIR)
pitches_count = count_files(PITCH_DIR, "_pitch.txt")
pr_count = count_files(PR_DIR, "_pitch.txt")

# --- REVENUE LOGIC ---
total_pipeline_revenue = 0.0
active_pipeline = []

if os.path.exists(PITCH_DIR):
    for filename in os.listdir(PITCH_DIR):
        if filename.endswith("_pitch.txt"):
            file_path = os.path.join(PITCH_DIR, filename)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Pull metadata using regex
            artist_m = re.search(r"ARTIST:\s*(.*)", content)
            room_m = re.search(r"ROOM TARGET:\s*(.*)", content)
            
            artist = artist_m.group(1).strip() if artist_m else filename.replace("_pitch.txt", "")
            room = room_m.group(1).strip() if room_m else "Unassigned"
            
            # Find dollar values in text to aggregate financial weights
            dollar_amounts = re.findall(r"\$(\d+(?:\,\d+)?(?:\.\d+)?)", content)
            val = 0.0
            if dollar_amounts:
                # Clean strings and parse values, targeting highest quote structure found
                val = max([float(d.replace(",", "")) for d in dollar_amounts])
            
            total_pipeline_revenue += val
            active_pipeline.append({"artist": artist, "room": room, "value": val})

# --- OUTPUT DASHBOARD DISPLAY ---
print("=" * 65)
print(f" 🔥 VOLT RECORDS ENTERPRISE DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 65)

print(f" 📈 PIPELINE VALUE : ${total_pipeline_revenue:,.2f}")
print("-" * 65)
print(f" 📥 Incoming Open Leads: {leads_count:<5} | 🎙️ Generated Pitches: {pitches_count}")
print(f" 🔒 Deployed/Closed:     {closed_count:<5} | 📰 PR Assets Prepped: {pr_count}")
print("=" * 65)

print(" 🎚️  ACTIVE DEALS REGISTERED IN PIPELINE:")
if not active_pipeline:
    print("    No active data profiles found in Outbound_Pitches.")
else:
    print(f"    {'ARTIST':<18} | {'TARGET ROOM':<15} | {'PROJECTED REVENUE':<18}")
    print("    " + "-" * 56)
    for deal in active_pipeline:
        print(f"    {deal['artist'][:16]:<18} | {deal['room'][:13]:<15} | ${deal['value']:,.2f}")

print("=" * 65)
print("  Commands: [python3 scraper.py] to hunt | [~/watchdog.sh] to process")
print("=" * 65)
