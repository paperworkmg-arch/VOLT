#!/usr/bin/env python3
"""
nightly_digest.py — Volt Records daily pipeline digest.

Emails paperworkmg@gmail.com a 60-second summary of the whole machine:
new leads, pitches written, drafts awaiting approval, sends, failures.
Scheduled via Autopilot (dashboard jobs table), cron nightly.
"""
import os
import re
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path.home() / "Omni-Studio"
LOG_FILE = BASE / "logs" / "digest.log"
CUTOFF = datetime.now() - timedelta(hours=24)

_env_path = BASE / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

EMAIL_ADDRESS = os.environ.get("VOLT_GMAIL_ADDRESS", "paperworkmg@gmail.com")
APP_PASSWORD = os.environ.get("VOLT_GMAIL_APP_PASSWORD", "")


def log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def recent_files(folder: Path, pattern: str = "*"):
    if not folder.exists():
        return []
    return [p for p in folder.glob(pattern)
            if p.is_file() and not p.name.startswith(".")
            and datetime.fromtimestamp(p.stat().st_mtime) > CUTOFF]


def artist_of(pitch_file: Path) -> str:
    try:
        m = re.search(r"^ARTIST: (.+)$", pitch_file.read_text(), re.MULTILINE)
        return m.group(1).strip() if m else pitch_file.stem
    except Exception:
        return pitch_file.stem


def build_digest() -> str:
    leads_pending = recent_files(BASE / "Incoming_Leads", "*.txt")
    leads_processed = [p for p in recent_files(BASE / "Closed_Deals", "*.txt")
                       if not p.name.startswith("FAILED_")]
    leads_skipped = recent_files(BASE / "Skipped_Leads", "*.txt")
    pitches = recent_files(BASE / "Outbound_Pitches", "*_pitch.txt")
    queue = sorted((BASE / "Send_Queue").glob("*.md")) if (BASE / "Send_Queue").exists() else []
    approved = sorted((BASE / "Send_Queue" / "Approved").glob("*.md"))
    sent = recent_files(BASE / "Send_Queue" / "Sent", "*.md")
    failed = recent_files(BASE / "Send_Queue" / "Failed", "*.md")

    L = []
    L.append(f"VOLT RECORDS — NIGHTLY DIGEST ({datetime.now():%A %b %d, %I:%M %p})")
    L.append("=" * 52)
    L.append("")
    L.append(f"📥 LEADS (last 24h)")
    L.append(f"  New captured:      {len(leads_pending) + len(leads_processed) + len(leads_skipped)}")
    L.append(f"  Turned to pitches: {len(pitches)}")
    L.append(f"  Skipped (junk):    {len(leads_skipped)}")
    L.append(f"  Still in queue:    {len(leads_pending)}")
    L.append("")
    L.append(f"📮 OUTBOUND")
    L.append(f"  Awaiting YOUR approval: {len(queue)}")
    for q in queue[:12]:
        L.append(f"    • {q.stem}")
    if len(queue) > 12:
        L.append(f"    … and {len(queue) - 12} more in Send_Queue/")
    L.append(f"  Approved, sending next cycle: {len(approved)}")
    L.append(f"  Sent (24h):  {len(sent)}")
    L.append(f"  Failed (24h): {len(failed)}")
    for f_ in failed[:5]:
        L.append(f"    ⚠️ {f_.stem}")
    L.append("")
    if pitches:
        L.append(f"🎤 NEW PITCHES (last 24h)")
        for p in pitches[:12]:
            L.append(f"  • {artist_of(p)}")
        if len(pitches) > 12:
            L.append(f"  … and {len(pitches) - 12} more")
        L.append("")
    L.append("—" * 52)
    L.append("ACTION: move drafts from Send_Queue/ into Send_Queue/Approved/")
    L.append("to fire them on the next 15-min cycle. IG DMs stay manual.")
    return "\n".join(L)


def send_digest(body: str):
    msg = MIMEText(body, "plain")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    msg["Subject"] = f"🎙️ Volt Nightly Digest — {datetime.now():%b %d}"
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())


if __name__ == "__main__":
    if not APP_PASSWORD:
        log("VOLT_GMAIL_APP_PASSWORD not set — check .env")
        raise SystemExit(1)
    digest = build_digest()
    send_digest(digest)
    log(f"Digest sent ({len(digest)} chars)")
