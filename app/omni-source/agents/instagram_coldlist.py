#!/usr/bin/env python3
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "Omni-Studio"
OUT_DIR = BASE / "Cold_Outreach_Drafts"
SENT_FILE = BASE / "coldlist_contacted.json"
LOG_FILE = BASE / "coldlist.log"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:14b"

OUT_DIR.mkdir(parents=True, exist_ok=True)

USERNAME_RE = re.compile(r"www\.instagram\.com/([A-Za-z0-9_.]+)/?")


def log(msg):
    line = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + msg
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_contacted():
    if SENT_FILE.exists():
        return set(json.loads(SENT_FILE.read_text()))
    return set()


def save_contacted(contacted):
    SENT_FILE.write_text(json.dumps(sorted(contacted)))


def call_ollama(prompt):
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data.get("response", "")
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def write_cold_dm(username):
    prompt = "You are a direct, no-fluff Atlanta studio manager writing a short cold DM to an Instagram follower named @" + username + ". You have NO information about this person\'s music, budget, or needs - do not invent any. This is a first touch, not a response to an inquiry. Write a 1-2 sentence casual DM introducing the studio and inviting them to reach out if they\'re ever looking to record. No corporate language. No made-up details about them. Respond with ONLY the DM text."
    return call_ollama(prompt)


def read_usernames(csv_path):
    usernames = []
    seen = set()
    with open(csv_path, newline="", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            row_text = ",".join(row)
            match = USERNAME_RE.search(row_text)
            if match:
                username = match.group(1)
                if username and username not in seen and username.lower() not in ("static", "p", "reel", "explore"):
                    seen.add(username)
                    usernames.append(username)
    return usernames


def safe_filename(username):
    return re.sub(r"[^A-Za-z0-9._-]", "_", username)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 instagram_coldlist.py <path_to_csv> [--limit N]")
        sys.exit(1)

    csv_path = Path(sys.argv[1]).expanduser()
    if not csv_path.exists():
        print("File not found: " + str(csv_path))
        sys.exit(1)

    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    usernames = read_usernames(csv_path)
    if limit:
        usernames = usernames[:limit]
    contacted = load_contacted()

    msg = "Extracted " + str(len(usernames)) + " usernames from " + csv_path.name
    if limit:
        msg += " (limited to " + str(limit) + ")"
    log(msg)

    new_count = 0
    for username in usernames:
        if username in contacted:
            continue
        try:
            dm_text = write_cold_dm(username)
        except Exception as e:
            log("  Failed on @" + username + ": " + str(e))
            continue

        fname = safe_filename(username)
        out_path = OUT_DIR / (fname + ".txt")
        out_path.write_text("TO: @" + username + "\nDM:\n" + dm_text + "\n")
        contacted.add(username)
        new_count += 1

        if new_count % 10 == 0:
            save_contacted(contacted)
            log("  Progress: " + str(new_count) + " drafted so far...")

    save_contacted(contacted)
    log("Done. " + str(new_count) + " new drafts written to " + str(OUT_DIR))


if __name__ == "__main__":
    main()
