#!/usr/bin/env python3
"""
studio_agent.py — Volt Records booking agent
"""
import os, re, json, time, shutil, urllib.request
from pathlib import Path
from datetime import datetime

BASE = Path.home() / "Omni-Studio"
LEADS_DIR   = BASE / "Incoming_Leads"
CLOSED_DIR  = BASE / "Closed_Deals"
PITCH_DIR   = BASE / "Outbound_Pitches"
SKIPPED_DIR = BASE / "Skipped_Leads"
LOG_FILE    = BASE / "logs" / "agent.log"

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "qwen3:14b"

RATES = {"A": 90, "B": 75}
ENGINEER_SURCHARGE = 35
BULK_DISCOUNT_HOURS = 12
BULK_DISCOUNT_PCT = 0.10

for d in (LEADS_DIR, CLOSED_DIR, PITCH_DIR, SKIPPED_DIR):
    d.mkdir(parents=True, exist_ok=True)

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data.get("response", "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text

def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))

def extract_facts(lead_text: str) -> dict:
    prompt = f"""Extract facts from this music-industry lead. Respond with ONLY a JSON object,
no explanation, no markdown fences.

Lead:
{lead_text}

JSON fields required:
{{
  "artist_name": <the specific artist/band name this lead is about, or null if none>,
  "is_artist_lead": <true ONLY if this is about a specific music artist and their release/activity; false for how-to articles, tutorials, industry/label business news, gear talk, and listicles>,
  "latest_work": <title of their single/EP/album/project mentioned, or null>,
  "genre_or_project": <short string describing their sound or scene>,
  "budget": <number or null>,
  "hours": <number or null>,
  "wants_premium_gear": <true or false>,
  "wants_dedicated_engineer": <true or false>,
  "tight_deadline": <true or false>
}}"""
    raw = call_ollama(prompt)
    return extract_json(raw)

def compute_deal(facts: dict) -> dict:
    room = "A" if facts.get("wants_premium_gear") else "B"
    rate = RATES[room]
    if facts.get("wants_dedicated_engineer"):
        rate += ENGINEER_SURCHARGE

    budget = facts.get("budget")
    hours = facts.get("hours")

    if hours:
        discounted_rate = rate * (1 - BULK_DISCOUNT_PCT) if hours > BULK_DISCOUNT_HOURS else rate
        total_cost = round(hours * discounted_rate, 2)
        structure = f"{hours} hrs x ${discounted_rate:.2f}/hr = ${total_cost}"
    elif budget:
        max_hours = round(budget / rate, 1)
        structure = f"${budget} budget / ${rate}/hr = {max_hours} hrs in {room} Room"
        total_cost = budget
    else:
        structure = f"Quoted at ${rate}/hr, no budget/hours stated yet"
        total_cost = None

    risk = "Green"
    if facts.get("tight_deadline") and budget and rate and budget / rate < 4:
        risk = "Red"
    elif budget and rate and budget / rate < 2:
        risk = "Yellow"

    return {"room": room, "rate": rate, "structure": structure,
            "total_cost": total_cost, "risk": risk}

def write_pitch(artist: str, facts: dict, deal: dict) -> str:
    latest = facts.get("latest_work")
    if latest:
        opener = f'- Congratulate them on their latest work "{latest}" BY NAME and say one specific thing you respect about it.'
    else:
        opener = "- Congratulate them on the recent press coverage and the momentum they're building. Do NOT invent or name a specific song, EP, or album title."
    prompt = f"""You are Mykel, a direct, no-fluff Atlanta studio owner (Volt Records)
reaching out to an emerging artist you just discovered.

Artist: {artist}
Their sound/scene: {facts.get('genre_or_project')}

Write a 3-4 sentence outreach message:
{opener}
- Offer a FREE first hour at your Atlanta studio (A Room $90/hr, B Room $75/hr after that).
- One line on why your rooms fit their sound.
- End by asking when they want to come through.

No corporate language. Never mention budgets, rate math, or that you found them online.
Only name a specific work if one was provided above. Respond with ONLY the pitch text."""
    return call_ollama(prompt)

def process_lead(path: Path):
    lead_text = path.read_text()
    log(f"Processing lead: {path.stem}")
    try:
        facts = extract_facts(lead_text)
        artist_name = (facts.get("artist_name") or "").strip()
        if not facts.get("is_artist_lead") or not artist_name:
            log(f"  Skipped (not an artist lead): {path.stem}")
            shutil.move(str(path), SKIPPED_DIR / path.name)
            return
        deal = compute_deal(facts)
        pitch = write_pitch(artist_name, facts, deal)
    except Exception as e:
        log(f"  Failed on {path.stem}: {e}")
        shutil.move(str(path), CLOSED_DIR / f"FAILED_{path.name}")
        return

    source_match = re.search(r"Contact: (\S+)", lead_text)
    source = source_match.group(1) if source_match else "unknown"
    safe = re.sub(r"[^a-zA-Z0-9]", "", artist_name)[:20] or path.stem
    suffix = path.stem.split("_")[-1]
    out = PITCH_DIR / f"{safe}_{suffix}_pitch.txt"
    out.write_text(
        f"ARTIST: {artist_name}\n"
        f"LATEST WORK: {facts.get('latest_work') or 'unknown'}\n"
        f"SOURCE: {source}\n"
        f"ROOM: {deal['room']} Room (${deal['rate']}/hr)\n"
        f"DEAL: {deal['structure']}\n"
        f"RISK: {deal['risk']}\n\n"
        f"PITCH:\n{pitch}\n"
    )
    shutil.move(str(path), CLOSED_DIR / path.name)
    log(f"  Pitch written for {artist_name}: {out}")

def main():
    log("Studio agent online. Watching Incoming_Leads/")
    while True:
        for path in sorted(LEADS_DIR.iterdir()):
            if path.is_file() and not path.name.startswith("."):
                process_lead(path)
        time.sleep(5)

if __name__ == "__main__":
    main()
