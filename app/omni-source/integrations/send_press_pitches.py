import os
import re
import smtplib
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DRY_RUN = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "paperworkmg@gmail.com"
SENDER_PASSWORD = "ylyp hfnz svmj geun"

PITCH_DIR = os.path.expanduser("~/Omni-Studio/Press_Pitches")
SENT_DIR = os.path.expanduser("~/Omni-Studio/Sent_Pitches")
os.makedirs(SENT_DIR, exist_ok=True)

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
    print("No national press pitches found.")
    exit()

try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    print("🔌 Press Pipeline SMTP Authenticated.")
except Exception as e:
    print(f"🛑 Press SMTP Login Failure: {str(e)}")
    exit()

for filename in os.listdir(PITCH_DIR):
    if filename.endswith("_pitch.txt") and not filename.startswith("."):
        file_path = os.path.join(PITCH_DIR, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            email_match = re.search(r"CONTACT EMAIL:\s*([^\n]+)", content)
            to_email = email_match.group(1).strip() if email_match else None
            
            subject_match = re.search(r"SUBJECT:\s*([^\n]+)", content)
            subject = subject_match.group(1).strip() if subject_match else "Grammy-Nominated Project Launch"
            
            body_parts = content.split("=========================================")
            raw_body = body_parts[-1].strip() if len(body_parts) > 1 else content
            clean_body = scrub_text(raw_body)
            
            if to_email:
                msg = MIMEMultipart()
                msg['From'] = SENDER_EMAIL
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(clean_body, 'plain'))
                
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
                print(f"📧 [PRESS SENT] -> {to_email}")
                shutil.move(file_path, os.path.join(SENT_DIR, filename))
        except Exception as e:
            print(f"🛑 Error on {filename}: {str(e)}")
server.quit()
