import os
import csv
import subprocess
from datetime import datetime

# --- CONFIGURATION ---
CSV_PATH = os.path.expanduser("~/national_media_contacts.csv")
OUTPUT_DIR = os.path.expanduser("~/Omni-Studio/Press_Pitches")
STUDIO_DIR = os.path.expanduser("~/Omni-Studio")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- THE WIDE-SCAN INJECTOR ---
def get_studio_inventory():
    inventory = []
    ignore_extensions = ['.py', '.sh', '.log', '.tmp', '.txt']
    ignore_folders = ['Press_Pitches', 'Incoming_Leads', 'Closed_Deals', 'Completed', 'DropFolder']
    
    if not os.path.exists(STUDIO_DIR):
        return "Omni-Studio directory not found."
        
    for root, dirs, files in os.walk(STUDIO_DIR):
        dirs[:] = [d for d in dirs if d not in ignore_folders and not d.startswith('.')]
        for file in files:
            if file.startswith('.'):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext not in ignore_extensions:
                rel_path = os.path.relpath(os.path.join(root, file), STUDIO_DIR)
                inventory.append(f"  - {rel_path}")
                
    if not inventory:
        return "No external media assets detected."
    return "\n".join(inventory)

LOCAL_ASSETS = get_studio_inventory()

# --- ACCREDITED BRAND MATRIX ---
FOUNDER_BIO = f"""
FOUNDER: Mykel T. Brooks (Instagram: @mykeltbrooks | Web: ITSMYKEL.COM)
ACCREDITATION: Grammy Award-Nominated Artist, Songwriter, and Executive Producer.
EXPERIENCE: 15+ years crafting records in the hip-hop/R&B ecosystem. Son of a Jamaican pastor.
THE MOVEMENT: Giving back to the local indie landscape by offering **1 Free Hour** of world-class studio time to independent Atlanta creators at Volt Records to show them what actual major-label master quality sounds like.

FLAGSHIP PROJECT: 'The Afterparty' featuring the hit single 'Toni Macaroni' (Live portal: http://sqtheafterparty.base44.app/)
STUDIO ENGINE: Volt Records (Atlanta, GA) featuring premium analog chains (Neumann/Tube-Tech).

LOCAL ASSETS SECURED ON DRIVE:
{LOCAL_ASSETS}
"""

if not os.path.exists(CSV_PATH): CSV_PATH = "national_media_contacts.csv"

print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏆 Indexing Grammy-Nominated Asset Vault.")

try:
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            outlet, media_type, email, notes = row['Outlet'], row['Type'], row['Contact Email'], row['Notes']
            clean_name = "".join(c for c in outlet if c.isalnum() or c in (' ', '_', '-')).rstrip().replace(' ', '_')
            output_file_path = os.path.join(OUTPUT_DIR, f"{clean_name}_pitch.txt")
            
            prompt = f"""
            You are a master publicist pitching a story on Grammy Award-nominated producer Mykel T. Brooks. He is disrupting the music industry with his platform 'The Afterparty' (featuring the track 'Toni Macaroni') and launching a bold initiative offering 1 free hour of elite studio tracking to independent artists at Volt Records.
            
            FOUNDER CONTEXT:
            {FOUNDER_BIO}
            
            TARGET OUTLET: {outlet} ({media_type}) | Notes: {notes}
            
            PR HOOK STRATEGY:
            - If Radio/Music: Highlight his Grammy nomination, his track 'Toni Macaroni' (http://sqtheafterparty.base44.app/), and the fact that he's giving Atlanta indie acts 1 free hour on a multi-platinum tracking chain.
            - If Business/Tech/Culture: Focus on how a Grammy-nominated creator built an app architecture at http://sqtheafterparty.base44.app/ to bypass streaming apps, using his Jamaican-bred resilience to give ownership back to the community via the free hour gateway.
            
            RULES:
            - Put 'Grammy-Nominated' in the email SUBJECT LINE.
            - Maximum 3 paragraphs. Clear call to action linking to http://sqtheafterparty.base44.app/.
            - Explicitly state that Toni_Macaroni_Master.wav and high-res media files are ready to send.
            
            Format output exactly like this:
            OUTLET: {outlet}
            CONTACT EMAIL: {email}
            =========================================
            SUBJECT: [Your Hook Title]
            
            [Your Pitch Body]
            """
            
            cmd = ["ollama", "run", "qwen3:14b", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            with open(output_file_path, "w", encoding='utf-8') as out_f: 
                out_f.write(result.stdout.strip())
                
            print(f"✓ Grammy-Tier Pitch updated for {outlet}")
            
except Exception as e: 
    print(f"🛑 Error: {str(e)}")
