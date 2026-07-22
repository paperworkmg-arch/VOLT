import imaplib
import email
import os
import re
import shutil
import random
from datetime import datetime

# --- CONFIGURATION ---
# Load secrets from .env (manual runs); orchestrator injects env for scheduled runs
_env_path = os.path.expanduser("~/Omni-Studio/.env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

IMAP_SERVER = "imap.gmail.com"
EMAIL_ADDRESS = os.environ.get("VOLT_GMAIL_ADDRESS", "paperworkmg@gmail.com")
APP_PASSWORD = os.environ.get("VOLT_GMAIL_APP_PASSWORD", "")
if not APP_PASSWORD:
    raise SystemExit("VOLT_GMAIL_APP_PASSWORD not set — check ~/Omni-Studio/.env")

PITCH_DIR = os.path.expanduser("~/Omni-Studio/Outbound_Pitches")
CONFIRMED_DIR = os.path.expanduser("~/Omni-Studio/Confirmed_Sessions")

os.makedirs(CONFIRMED_DIR, exist_ok=True)

print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 Volt Income Watchdog Active. Scanning for deposits...")

def generate_gate_code():
    # Generates a professional 4-digit studio gate entry code
    return f"*{random.randint(1000, 9999)}#"

def check_for_payments():
    try:
        # Connect to Gmail IMAP safely
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")
        
        # Search for unread or skipped transaction notifications from past artists networks
        # Looks for subject lines or bodies containing standard money-received alerts
        status, messages = mail.search(None, '(UNSEEN OR (FROM "cash@square.com") (FROM "no-reply@zellepay.com") (FROM "venmo@venmo.com"))')
        
        if status != "OK" or not messages[0]:
            print("   ✓ No new payment alerts detected in inbox.")
            return

        for msg_id in messages[0].split():
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = str(msg["Subject"])
                    body = ""
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    full_alert_text = f"{subject} {body}".lower()
                    
                    # Look for active pitches to reconcile against
                    for filename in os.listdir(PITCH_DIR):
                        if filename.endswith("_pitch.txt"):
                            artist_name = filename.replace("_pitch.txt", "")
                            
                            # Clean up strings to match artist names to deposit receipts smoothly
                            clean_artist = re.sub(r'[^a-zA-Z0-9]', '', artist_name).lower()
                            
                            # Check if the payment text contains keywords indicating a successful receipt
                            if clean_artist in full_alert_text and any(x in full_alert_text for x in ["sent you", "received", "completed", "payment"]):
                                print(f"🔥 [MATCH] Cash match verified for Artist: {artist_name}!")
                                
                                # Generate their automated security credentials
                                gate_code = generate_gate_code()
                                
                                # Move their file to Confirmed_Sessions
                                old_pitch_path = os.path.join(PITCH_DIR, filename)
                                new_confirm_path = os.path.join(CONFIRMED_DIR, f"{artist_name}_confirmed.txt")
                                
                                with open(old_pitch_path, "r", encoding="utf-8") as f:
                                    pitch_data = f.read()
                                    
                                with open(new_confirm_path, "w", encoding="utf-8") as f:
                                    f.write(f"STATUS: CONFIRMED & PAID\n")
                                    f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                    f.write(f"ASSIGNED STUDIO GATE CODE: {gate_code}\n")
                                    f.write("=" * 40 + "\n")
                                    f.write(pitch_data)
                                    
                                os.remove(old_pitch_path)
                                print(f"   🔒 Security Gate Code {gate_code} generated and assigned to {artist_name}.")
                                
        mail.logout()
        
    except Exception as e:
        print(f"🛑 Income Watchdog Error: {str(e)}")

if __name__ == "__main__":
    check_for_payments()
