#!/usr/bin/env python3
"""
contact_enricher.py — Volt Records pitch contact enrichment.

Scans Outbound_Pitches for pitch files missing a CONTACTS: block, fetches the
SOURCE article, and extracts artist contact routes (Instagram, X/Twitter,
Linktree, email). Appends results to the pitch file. Idempotent: files that
already have CONTACTS: are skipped.
"""
import os
import re
import time
import urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "Omni-Studio"
PITCH_DIR = BASE / "Outbound_Pitches"
LOG_FILE = BASE / "logs" / "enricher.log"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 20
MAX_HTML = 400_000

# Handles that belong to platforms/publications, never to the artist
HANDLE_BLOCKLIST = {
    "p", "reel", "reels", "explore", "stories", "tv", "accounts", "direct",
    "earmilk", "atwoodmagazine", "respectmag", "respect_mag", "nme",
    "google", "news", "share", "intent", "home", "search", "hashtag",
}
EMAIL_JUNK = ("example.com", "sentry", "wixpress", "wordpress", "@2x", ".png",
              ".jpg", ".webp", "godaddy", "privacy", "noreply", "no-reply")


def log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read(MAX_HTML).decode("utf-8", errors="ignore")


def resolve_google_news(url: str, html: str) -> str:
    """Google News RSS links are interstitials; dig out the publisher URL."""
    if "news.google.com" not in url:
        return url
    candidates = re.findall(r'https?://[^\s"\'<>\\]+', html)
    for c in candidates:
        host = re.sub(r"^https?://", "", c).split("/")[0]
        if not any(bad in host for bad in ("google.", "gstatic.", "googleusercontent.", "ggpht.", "youtube.")):
            return c
    return url


def clean_handle(h: str) -> str:
    return h.strip("/").split("?")[0].lower()


def extract_contacts(html: str) -> dict:
    contacts = {"instagram": [], "x": [], "linktree": [], "email": []}

    for h in re.findall(r'instagram\.com/([A-Za-z0-9_.]{2,30})', html):
        h = clean_handle(h)
        if h and h not in HANDLE_BLOCKLIST and h not in contacts["instagram"]:
            contacts["instagram"].append(h)

    for h in re.findall(r'(?:twitter|x)\.com/([A-Za-z0-9_]{2,20})', html):
        h = clean_handle(h)
        if h and h not in HANDLE_BLOCKLIST and h not in contacts["x"]:
            contacts["x"].append(h)

    for h in re.findall(r'linktr\.ee/([A-Za-z0-9_.]{2,30})', html):
        h = clean_handle(h)
        if h and h not in contacts["linktree"]:
            contacts["linktree"].append(h)

    for e in re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html):
        e = e.lower()
        if not any(j in e for j in EMAIL_JUNK) and e not in contacts["email"]:
            contacts["email"].append(e)

    return contacts


def enrich_pitch(path: Path) -> bool:
    text = path.read_text()
    if "CONTACTS:" in text:
        return False
    source_match = re.search(r"SOURCE: (\S+)", text)
    if not source_match or source_match.group(1) == "unknown":
        with open(path, "a") as f:
            f.write("\nCONTACTS:\nno source link — manual lookup needed\n")
        return True

    url = source_match.group(1)
    try:
        html = fetch(url)
        real_url = resolve_google_news(url, html)
        if real_url != url:
            html = fetch(real_url)
        contacts = extract_contacts(html)
    except Exception as e:
        log(f"  fetch failed for {path.name}: {e}")
        contacts = {"instagram": [], "x": [], "linktree": [], "email": []}

    lines = ["\nCONTACTS:"]
    found = False
    for h in contacts["instagram"][:2]:
        lines.append(f"instagram: @{h} (https://instagram.com/{h})")
        found = True
    for h in contacts["x"][:1]:
        lines.append(f"x: @{h} (https://x.com/{h})")
        found = True
    for h in contacts["linktree"][:1]:
        lines.append(f"linktree: https://linktr.ee/{h}")
        found = True
    for e in contacts["email"][:2]:
        lines.append(f"email: {e}")
        found = True
    if not found:
        lines.append("none found — manual lookup needed")

    with open(path, "a") as f:
        f.write("\n".join(lines) + "\n")
    return True


def main():
    pitches = sorted(PITCH_DIR.glob("*_pitch.txt"))
    enriched = 0
    for path in pitches:
        try:
            if enrich_pitch(path):
                enriched += 1
                log(f"  enriched: {path.name}")
        except Exception as e:
            log(f"  error on {path.name}: {e}")
        time.sleep(0.5)  # be polite to publishers
    log(f"Enrichment pass complete: {enriched} new / {len(pitches)} total pitches")


if __name__ == "__main__":
    main()
