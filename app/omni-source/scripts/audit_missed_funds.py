"""
Volt Records — Historical Missed-Payment Auditor.

Scans the last N days of payment receipts (Cash App / Venmo / Zelle) via Gmail
IMAP, extracts sender names, and injects them into the CRM as
'PENDING VERIFICATION' leads so no past client falls through the cracks.

Realtime deposit detection lives in scripts/income_watchdog.py; this is the
one-off / periodic historical sweep. Runs fine as a manual script:

    .venv/bin/python scripts/audit_missed_funds.py
"""
import os
import re
import email
import imaplib
import sqlite3
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('audit-missed-funds')

# --- CONFIGURATION ---
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

PAYMENT_SENDERS = ["cash@square.com", "venmo@venmo.com", "no-reply@zellepay.com"]
DB_PATH = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')
LOOKBACK_DAYS = 180


def _extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")
    return body


def _extract_name(text: str):
    """Pull the payer name out of a receipt like 'John Doe sent you $50'."""
    lowered = text.lower()
    for marker in ("sent you", "paid you"):
        if marker in lowered:
            idx = lowered.index(marker)
            raw = text[:idx]
            # Keep the last line/fragment before the marker, strip labels like "Cash App:"
            raw = raw.strip().splitlines()[-1] if raw.strip() else ""
            raw = re.sub(r'(?i)cash app:|venmo:|zelle:', '', raw)
            raw = re.sub(r'[^a-zA-Z\s]', '', raw).strip()
            # Take at most the last 4 words as the name
            words = raw.split()[-4:]
            if words:
                return " ".join(words).title()
    return None


def audit_missed_payments(days: int = LOOKBACK_DAYS):
    if not APP_PASSWORD:
        logger.error("VOLT_GMAIL_APP_PASSWORD not set — check ~/Omni-Studio/.env")
        return

    since = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
    # OR the payment senders together, AND with the SINCE window
    or_clause = f'(OR (OR (FROM "{PAYMENT_SENDERS[0]}") (FROM "{PAYMENT_SENDERS[1]}")) (FROM "{PAYMENT_SENDERS[2]}"))'

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, APP_PASSWORD)
        mail.select("inbox")
        status, data = mail.search(None, f'(SINCE "{since}")', or_clause)
        if status != "OK" or not data or not data[0]:
            logger.info("✅ No payment receipts found in the last %d days.", days)
            mail.logout()
            return

        msg_ids = data[0].split()
        logger.info("🔍 Found %d receipt candidates from the last %d days. Analyzing...", len(msg_ids), days)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
            city TEXT, status TEXT DEFAULT 'SCRAPED', gate_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        missed_count = 0
        for msg_id in msg_ids:
            _, fetched = mail.fetch(msg_id, "(RFC822)")
            if not fetched or not isinstance(fetched[0], tuple):
                continue
            msg = email.message_from_bytes(fetched[0][1])
            body = _extract_body(msg).lower()
            if 'sent you' not in body and 'paid you' not in body:
                continue
            name = _extract_name(_extract_body(msg))
            if not name:
                continue
            placeholder_email = f"{name.replace(' ', '').lower()}@needs_contact.com"
            try:
                cursor.execute(
                    "INSERT INTO leads (name, email, city, status) VALUES (?, ?, ?, 'PENDING VERIFICATION')",
                    (name, placeholder_email, 'Unknown')
                )
                conn.commit()
                logger.info("💰 LOGGED MISSED PAYMENT: %s", name)
                missed_count += 1
            except sqlite3.IntegrityError:
                pass  # Already in DB

        conn.close()
        mail.logout()
        logger.info("✅ Audit complete. %d missed payments added as 'PENDING VERIFICATION'.", missed_count)

    except imaplib.IMAP4.error as e:
        logger.error("🛑 Gmail login failed: %s", e)
    except Exception as e:
        logger.error("🛑 Error during audit: %s", e)


if __name__ == "__main__":
    audit_missed_payments()
