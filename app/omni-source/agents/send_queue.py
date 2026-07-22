#!/usr/bin/env python3
"""
send_queue.py — Volt Records approval-based send queue.

For every enriched pitch (CONTACTS: block with real contacts), drafts a
ready-to-send Instagram DM and email via local Ollama, and drops one review
file per artist into Send_Queue/. Nothing is ever sent automatically —
the user reviews, edits, and fires manually.

Idempotent: an artist with an existing Send_Queue file is skipped.
"""
import os
import re
import json
import urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "Omni-Studio"
PITCH_DIR = BASE / "Outbound_Pitches"
QUEUE_DIR = BASE / "Send_Queue"
LOG_FILE = BASE / "logs" / "send_queue.log"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:14b"

QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False, "think": False,
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data.get("response", "")
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def parse_pitch(text: str) -> dict:
    def field(name):
        m = re.search(rf"^{name}: (.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""
    pitch_match = re.search(r"PITCH:\n(.*?)\nCONTACTS:", text, re.DOTALL)
    contacts_match = re.search(r"CONTACTS:\n(.*)$", text, re.DOTALL)
    return {
        "artist": field("ARTIST"),
        "latest": field("LATEST WORK"),
        "source": field("SOURCE"),
        "pitch": pitch_match.group(1).strip() if pitch_match else "",
        "contacts": contacts_match.group(1).strip() if contacts_match else "",
    }


def has_real_contacts(contacts: str) -> bool:
    return bool(contacts) and "manual lookup" not in contacts and "no source" not in contacts


def draft_messages(artist: str, latest: str, pitch: str) -> dict:
    prompt = f"""You are Mykel, owner of Volt Records studio in Atlanta. Turn this outreach
pitch into two ready-to-send messages for the artist {artist}.

Original pitch:
{pitch}

Respond with ONLY a JSON object, no markdown fences:
{{
  "dm": "<Instagram DM, max 280 characters, casual and warm, no hashtags, mention the free first hour, end with a question>",
  "email_subject": "<short subject line, no clickbait>",
  "email_body": "<4-6 sentence email version of the pitch, plain text, sign off as Mykel, Volt Records, Atlanta>"
}}
Only reference their work '{latest}' if it is a real title, never invent one."""
    raw = call_ollama(prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON in model output")
    return json.loads(match.group(0))


def queue_pitch(path: Path) -> bool:
    data = parse_pitch(path.read_text())
    if not data["artist"] or not has_real_contacts(data["contacts"]):
        return False

    safe = re.sub(r"[^a-zA-Z0-9]", "", data["artist"])[:25] or path.stem
    out = QUEUE_DIR / f"{safe}.md"
    if out.exists():
        return False

    msgs = draft_messages(data["artist"], data["latest"], data["pitch"])
    out.write_text(
        f"# Send Queue — {data['artist']}\n\n"
        f"**Latest work:** {data['latest'] or 'unknown'}\n"
        f"**Source:** {data['source']}\n\n"
        f"## Contacts\n```\n{data['contacts']}\n```\n\n"
        f"## Instagram DM (280 chars)\n{msgs['dm']}\n\n"
        f"## Email\n**Subject:** {msgs['email_subject']}\n\n"
        f"{msgs['email_body']}\n\n"
        f"---\n*Drafted {datetime.now():%Y-%m-%d %H:%M}. To AUTO-SEND the email: move this file into "
        f"Send_Queue/Approved/ — it goes out on the next 15-min cycle and lands in Sent/. "
        f"IG DMs are always manual. Delete this file to regenerate.*\n"
    )
    return True


def main():
    queued = 0
    for path in sorted(PITCH_DIR.glob("*_pitch.txt")):
        try:
            if queue_pitch(path):
                queued += 1
                log(f"  queued: {path.name}")
        except Exception as e:
            log(f"  error on {path.name}: {e}")
    log(f"Send queue pass complete: {queued} new drafts")


if __name__ == "__main__":
    main()
