#!/usr/bin/env python3
"""
approved_sender.py — Volt Records approval-gated email sender.

Watches Send_Queue/Approved/ for drafts the user has approved (by moving the
file there) and sends the EMAIL version via Gmail SMTP. Instagram DMs always
stay manual — there is no safe IG send API.

Flow: Send_Queue/<artist>.md → user moves to Approved/ → sent → moved to Sent/.
Failures move to Failed/ with the error noted. Nothing sends without the file
physically being in Approved/.
"""
import os
import re
import smtplib
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "Omni-Studio"
QUEUE_DIR = BASE / "Send_Queue"
APPROVED_DIR = QUEUE_DIR / "Approved"
SENT_DIR = QUEUE_DIR / "Sent"
FAILED_DIR = QUEUE_DIR / "Failed"
LOG_FILE = BASE / "logs" / "sender.log"

for d in (APPROVED_DIR, SENT_DIR, FAILED_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Load secrets from .env
_env_path = BASE / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get("VOLT_GMAIL_ADDRESS", "paperworkmg@gmail.com")
APP_PASSWORD = os.environ.get("VOLT_GMAIL_APP_PASSWORD", "")


def log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def parse_draft(text: str) -> dict:
    email_match = re.search(r"^email: (\S+@\S+)$", text, re.MULTILINE)
    subject_match = re.search(r"\*\*Subject:\*\* (.+)", text)
    body_match = re.search(r"\*\*Subject:\*\* .+\n\n(.*?)\n\n---", text, re.DOTALL)
    return {
        "to": email_match.group(1).strip() if email_match else None,
        "subject": subject_match.group(1).strip() if subject_match else "Studio time at Volt Records",
        "body": body_match.group(1).strip() if body_match else None,
    }


def send_email(to: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to, msg.as_string())


def process_approved(path: Path):
    text = path.read_text()
    draft = parse_draft(text)
    if not draft["to"] or not draft["body"]:
        log(f"  {path.name}: no email contact or body — IG/manual only, leaving in Approved/")
        return
    try:
        send_email(draft["to"], draft["subject"], draft["body"])
        with open(path, "a") as f:
            f.write(f"\n**SENT** to {draft['to']} at {datetime.now():%Y-%m-%d %H:%M}\n")
        shutil.move(str(path), SENT_DIR / path.name)
        log(f"  ✅ SENT {path.name} → {draft['to']}")
    except Exception as e:
        with open(path, "a") as f:
            f.write(f"\n**SEND FAILED** at {datetime.now():%Y-%m-%d %H:%M}: {e}\n")
        shutil.move(str(path), FAILED_DIR / path.name)
        log(f"  ❌ FAILED {path.name}: {e}")


def main():
    if not APP_PASSWORD:
        log("VOLT_GMAIL_APP_PASSWORD not set — check .env")
        return
    approved = sorted(APPROVED_DIR.glob("*.md"))
    for path in approved:
        try:
            process_approved(path)
        except Exception as e:
            log(f"  error on {path.name}: {e}")
    log(f"Sender pass complete: {len(approved)} approved draft(s) processed")


if __name__ == "__main__":
    main()
