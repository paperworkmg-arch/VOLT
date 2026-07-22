import os
import re
import smtplib
import shutil
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DRY_RUN = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "paperworkmg@gmail.com"
SENDER_PASSWORD = "ylyp hfnz svmj geun"

PITCH_DIR = os.path.expanduser("~/Omni-Studio/Outbound_Pitches")
CONTACTED_DIR = os.path.expanduser("~/Omni-Studio/Contacted_Leads")
CLOSED_DIR = os.path.expanduser("~/Omni-Studio/Closed_Deals")
os.makedirs(CONTACTED_DIR, exist_ok=True)

def scrub_text(text):
    if not text: return ""
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    cleaned = re.sub(r'\[\d+[A-Z]\s*\[[A-Z]', '', cleaned)
    cleaned = re.sub(r'\[\d+[A-Z]', '', cleaned)
    cleaned = re.sub(r'\bth\s+the\b', 'the', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(\w+)\b\s+\1\b', r'\1', cleaned)
    cleaned = re.sub(r'\b(\w+)\.\s+\1\b', r'\1.', cleaned)
    return "\n".join([line.strip() for line in cleaned.splitlines() if line.strip()])

if not os.path.exists(PITCH_DIR) or not os.listdir(PITCH_DIR):
    print("No outbound artist pitches found.")
    exit()

try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    print("🔌 A&R Pipeline SMTP Authenticated.")
except Exception as e:
    print(f"🛑 A&R SMTP Login Failure: {str(e)}")
    exit()

for filename in os.listdir(PITCH_DIR):
    if filename.endswith("_pitch.txt") and not filename.startswith("."):
        artist_name = filename.replace("_pitch.txt", "")
        pitch_path = os.path.join(PITCH_DIR, filename)
        closed_path = os.path.join(CLOSED_DIR, f"{artist_name}.txt")
        
        try:
            with open(pitch_path, 'r', encoding='utf-8') as f:
                pitch_content = f.read()
            pitch_parts = pitch_content.split("PITCH:")
            raw_body = pitch_parts[-1].strip() if len(pitch_parts) > 1 else pitch_content
            clean_body = scrub_text(raw_body)
            
            to_email = None
            if os.path.exists(closed_path):
                with open(closed_path, 'r', encoding='utf-8') as f:
                    lead_content = f.read()
                email_match = re.search(r"Contact:\s*(https://[^\s]+|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", lead_content)
                if email_match:
                    to_email = email_match.group(1).strip()
            
            if to_email and "@" in to_email:
                subject = "Exclusive Session Offer: Volt Records Atlanta (First Hour Free)"
                msg = MIMEMultipart()
                msg['From'] = SENDER_EMAIL
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(clean_body, 'plain'))
                
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
                print(f"📧 [ARTIST OUTBOUND SENT] -> {artist_name} ({to_email})")
                shutil.move(pitch_path, os.path.join(CONTACTED_DIR, filename))
                time.sleep(15)
        except Exception as e:
            print(f"🛑 Error targeting {artist_name}: {str(e)}")
server.quit()
