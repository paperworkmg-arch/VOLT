import imaplib
import smtplib
import email
import os
import re
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get("VOLT_GMAIL_ADDRESS", "paperworkmg@gmail.com")
APP_PASSWORD = os.environ.get("VOLT_GMAIL_APP_PASSWORD", "")
if not APP_PASSWORD:
    raise SystemExit("VOLT_GMAIL_APP_PASSWORD not set — check ~/Omni-Studio/.env")

print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Autonomous Inbound AI Agent Online. Monitoring inbox...")

def scrub_text(text):
    if not text: return ""
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    cleaned = re.sub(r'\[\d+[A-Z]\s*\[[A-Z]', '', cleaned)
    cleaned = re.sub(r'\[\d+[A-Z]', '', cleaned)
    cleaned = re.sub(r'\b(\w+)\b\s+\1\b', r'\1', cleaned)
    return "\n".join([line.strip() for line in cleaned.splitlines() if line.strip()])

def handle_conversations():
    try:
        # Connect to Inbox
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")
        
        # DEBUG FIX 1: Fetch ALL unseen messages and filter in Python to bypass Gmail's strict IMAP syntax rules
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != "OK" or not messages[0]:
            print("   ✓ Inbox clear. No unread artist replies.")
            mail.logout()
            return

        # Initialize SMTP Server for replies
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)

        # System/spam senders to ignore completely
        ignore_senders = [
            "cash@square.com", "no-reply@zellepay.com", "venmo@venmo.com",
            EMAIL_ADDRESS.lower(),
            "noreply@github.com", "noreply-accounts@google.com",
            "no-reply@accounts.google.com", "mailer-daemon@googlemail.com",
            "noreply@x.ai", "noreply@uvi.net", "noreply@swagbucks.com",
            "noreply@mail.squarespace.com", "noreply@skool.com",
            "webmail@uaudio.com", "noreply@accounts.google.com",
            "reply@ss.email.nextdoor.com",
        ]

        # Subject keywords that indicate non-studio emails
        ignore_subjects = [
            "github", "security alert", "verification code", "verify",
            "delivery status", "delivery incomplete", "unsubscribe",
            "account data", "oauth", "third-party", "login",
            "password", "reset", "confirm", "welcome to",
        ]

        for msg_id in messages[0].split():
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    sender = str(msg.get("From", ""))
                    subject = str(msg.get("Subject", ""))
                    
                    # Check if this is a payment notification or our own sent mail
                    if any(ignored in sender.lower() for ignored in ignore_senders):
                        mail.store(msg_id, '+FLAGS', '\\Seen')
                        continue
                    
                    # Check if subject indicates non-studio email
                    subject_lower = subject.lower()
                    if any(kw in subject_lower for kw in ignore_subjects):
                        mail.store(msg_id, '+FLAGS', '\\Seen')
                        continue
                    
                    # Extract body first so filters and the AI persona can use it
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            # DEBUG FIX 3: Robust payload extraction to prevent encoding crashes
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body += payload.decode(errors="ignore")
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")

                    # Check body for system email patterns
                    body_lower = body.lower()[:2000]
                    body_ignore = [
                        "unsubscribe", "do not reply", "do-not-reply",
                        "delivery incomplete", "delivery status",
                        "security alert", "account data", "oauth",
                        "third-party", "verification code",
                    ]
                    if any(kw in body_lower for kw in body_ignore):
                        mail.store(msg_id, '+FLAGS', '\\Seen')
                        continue
                    
                    print(f"💬 Incoming message discovered from: {sender}")
                    
                    # Trigger Mac Notification
                    clean_sender = sender.split("<")[0].strip().replace('"', '')
                    try:
                        subprocess.run(["osascript", "-e", f'display notification "Artist {clean_sender} replied! AI responding..." with title "🎙️ VOLT LIVE CHAT" sound name "Ping"'], check=False)
                    except:
                        pass # Ignore if notification system is busy
                    
                    # --- AI PERSONA ENGINE ---
                    prompt = f"""
                    You are Mykel T. Brooks, a Grammy Award-nominated music producer and founder of Volt Records in Atlanta. 
                    An artist just replied to your "First Hour Free" promotional studio offer. Respond exactly as Mykel would.
                    
                    YOUR STYLE:
                    - Elite, confident, and warm but hyper-direct. No corporate speak.
                    - Call them "fam" or use their name naturally if you know it.
                    - Keep your focus squarely on getting them to commit to a block of tracking time at the studio (A Room: $90/hr, B Room: $75/hr). Remind them the first hour is free.
                    - If they are ready to book, tell them to reply with their target day/time and send their lock-in deposit via CashApp/Zelle.
                    
                    ARTIST EMAIL CONTENT:
                    Sender: {sender}
                    Subject: {subject}
                    Message: "{body}"
                    
                    INSTRUCTIONS:
                    Write a punchy response under 4 sentences max. Sign off as "Mykel T. Brooks // Volt Records". Do not include extra AI text.
                    """
                    
                    # DEBUG FIX 2: Timeout added so a slow local LLM won't hang the master loop
                    cmd = ["ollama", "run", "qwen3:14b", prompt]
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
                    ai_reply = scrub_text(result.stdout.strip())
                    
                    # Prepare and transmit email reply
                    reply_msg = MIMEMultipart()
                    reply_msg['From'] = EMAIL_ADDRESS
                    
                    # Ensure we extract just the email address for the 'To' field
                    to_email_match = re.search(r'<([^>]+)>', sender)
                    clean_to = to_email_match.group(1) if to_email_match else sender
                    
                    reply_msg['To'] = clean_to
                    reply_msg['Subject'] = f"Re: {subject.replace('Re: ', '').replace('re: ', '')}"
                    reply_msg.attach(MIMEText(ai_reply, 'plain'))
                    
                    server.sendmail(EMAIL_ADDRESS, clean_to, reply_msg.as_string())
                    print(f"📤 [AUTO-RESPONDED] -> Sent tailored reply to {clean_to}")
                    
                    # Mark email as read
                    mail.store(msg_id, '+FLAGS', '\\Seen')
                    
        server.quit()
        mail.logout()
        
    except Exception as e:
        print(f"🛑 Inbound Conversation Error: {str(e)}")

if __name__ == "__main__":
    handle_conversations()
