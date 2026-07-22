#!/usr/bin/env python3
"""
Catalog DSP Vetting Pipeline v2 — Machine-Listening Engine.
Loads raw audio, extracts structural/spectral DNA via librosa, translates to a
semantic profile, and hands it to local Gemma (Ollama) for A&R appraisal.
Outputs analysis_results.json + TOP15 summary + FFL/Ledger ingest + email.
"""

import os
import re
import json
import logging
import concurrent.futures
import requests
import numpy as np
import librosa

from pathlib import Path
from datetime import datetime, date

# --- Logging Setup ---
_HOME = Path.home()
_OMNI = _HOME / "Omni-Studio"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(str(_OMNI / "catalog_analysis.log")),
        logging.StreamHandler()
    ]
)

CATALOG_DIR = str(_HOME / "PMG_Vault" / "Billboard_Catalog")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma"
MAX_WORKERS = 2
OUTPUT_DIR = _OMNI / "output" / "catalog_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_JSON = str(_OMNI / "analysis_results.json")
SUMMARY = OUTPUT_DIR / "TOP15_summary.txt"
DB = str(_HOME / ".omni" / "omni.db")
TO = "paperworkmg@gmail.com"

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def analyze_raw_audio(file_path):
    """Listens to the audio file and extracts structural/spectral features via DSP."""
    try:
        y, sr = librosa.load(file_path, duration=45, sr=22050)

        # 1. Rhythm (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if isinstance(tempo, np.ndarray) else float(tempo)
        if bpm < 40 or bpm > 240:
            bpm = 120.0

        # 2. Key/Scale via Chromagram
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_vals = np.mean(chroma, axis=1)
        estimated_key = NOTE_NAMES[np.argmax(chroma_vals)]

        # 3. Structural Velocity & Hook Density (RMS Energy Variance)
        rms = librosa.feature.rms(y=y)[0]
        energy_variance = float(np.var(rms) * 1000)
        avg_energy = float(np.mean(rms))
        structural_velocity = round(min(10.0, max(1.0, energy_variance * 2.5)), 1)
        energy_density = round(min(10.0, max(1.0, avg_energy * 20)), 1)

        # 4. Timbral Profile (Spectral Centroid)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_brightness = float(np.mean(centroid))
        brightness_profile = "Bright/Aggressive" if avg_brightness > 2400 else "Warm/Dark"

        return {
            "bpm": round(bpm, 1),
            "key": estimated_key,
            "structural_velocity": structural_velocity,
            "brightness_profile": brightness_profile,
            "energy_density": energy_density,
        }
    except Exception as e:
        logging.error(f"DSP Extraction failed for {Path(file_path).name}: {str(e)}")
        return None


def run_hitmaker_judgment(audio_metrics, track_name):
    """Queries local Ollama to process DSP metrics into definitive A&R metrics."""
    system_prompt = (
        f"You are an elite A&R Asset Valuation Engine analyzing: '{track_name}'.\n"
        f"The DSP layer extracted these audio specifications:\n"
        f"- Tempo: {audio_metrics['bpm']} BPM\n"
        f"- Key: {audio_metrics['key']}\n"
        f"- Energy Density: {audio_metrics['energy_density']}/10\n"
        f"- Structural Velocity (Hook Potential): {audio_metrics['structural_velocity']}/10\n"
        f"- Timbral Profile: {audio_metrics['brightness_profile']}\n\n"
        f"TASK:\n"
        f"1. Generate a short 5-word Suno custom style prompt.\n"
        f"2. Output a definitive valuation using this exact plain text block format:\n"
        f"ALPHA SCORE: [Compute a value 0.0 to 10.0]\n"
        f"MARKET MODULARITY: [Compute a value 0.0 to 10.0 based on social loop potential]\n"
        f"VERDICT: [Provide a 1-sentence financial asset routing decision]"
    )
    payload = {"model": MODEL_NAME, "prompt": system_prompt, "stream": False}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        logging.error(f"Local LLM completion failed for {track_name}: {str(e)}")
        return ""


def parse_llm_response(text, dsp_metrics):
    """Robust regex parsing to capture raw or markdown formatted scores cleanly."""
    alpha_match = re.search(r'(?:ALPHA\s+SCORE|SCORE)[:\s\*]+([0-9\.]+)', text, re.IGNORECASE)
    mod_match = re.search(r'MARKET\s+MODULARITY[:\s\*]+([0-9\.]+)', text, re.IGNORECASE)
    verdict_match = re.search(r'VERDICT[:\s\*]+(.*)', text, re.IGNORECASE)

    alpha = float(alpha_match.group(1)) if alpha_match else 0.0
    modularity = float(mod_match.group(1)) if mod_match else 0.0
    verdict = verdict_match.group(1).strip() if verdict_match else "No text verdict generated."

    # Unified HPI score using the 3-Factor algorithm
    hpi = (alpha * 0.4) + (dsp_metrics['structural_velocity'] * 0.4) + (modularity * 0.2)

    return {
        "alpha": round(alpha, 1),
        "structural_velocity": dsp_metrics['structural_velocity'],
        "market_modularity": round(modularity, 1),
        "hpi": round(hpi, 2),
        "verdict": verdict,
    }


def process_single_track(file_path):
    """Worker pipeline: ingestion, DSP features, LLM scoring, parsing."""
    track_name = Path(file_path).name
    logging.info(f"Listening & Analyzing: {track_name}")

    metrics = analyze_raw_audio(file_path)
    if not metrics:
        return None

    llm_raw_output = run_hitmaker_judgment(metrics, track_name)
    if not llm_raw_output:
        return None

    parsed = parse_llm_response(llm_raw_output, metrics)

    result = {
        "track": track_name,
        "bpm": metrics["bpm"],
        "key": metrics["key"],
        "brightness": metrics["brightness_profile"],
        "energy_density": metrics["energy_density"],
        **parsed,
    }
    logging.info(f"Processed: {track_name} -> HPI: {result['hpi']} (Alpha: {result['alpha']})")
    return result


def generate_summary(final_ledger):
    scored = [r for r in final_ledger if r.get("hpi", 0) > 0]
    top = sorted(scored, key=lambda x: x["hpi"], reverse=True)[:15]
    lines = []
    lines.append("=" * 72)
    lines.append("PMG / BILLBOARD CATALOG - TOP 15 VETTED TRACKS (DSP MACHINE-LISTENING)")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Total analyzed: {len(final_ledger)} | Scored: {len(scored)}")
    lines.append("=" * 72)
    for i, t in enumerate(top, 1):
        lines.append(
            f"{i:2d}. {t['track'][:42]:42s} HPI {t['hpi']:5.2f} "
            f"(A{t['alpha']} SV{t['structural_velocity']} MM{t['market_modularity']}) "
            f"{t['bpm']}BPM {t['key']} {t['brightness']}"
        )
        lines.append(f"     -> {t['verdict'][:80]}")
    lines.append("=" * 72)
    out = "\n".join(lines)
    SUMMARY.write_text(out)
    return out, top


def ingest_ffl_ledger(top):
    import sqlite3
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT,
            city TEXT, role TEXT, equity_score REAL DEFAULT 0, ffl_status TEXT DEFAULT 'new',
            notes TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS ffl_outreach (
            id INTEGER PRIMARY KEY AUTOINCREMENT, contact_id INTEGER, message TEXT, sent INTEGER DEFAULT 0,
            reply TEXT, equity_score REAL DEFAULT 0, dynamic_price REAL DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, amount REAL DEFAULT 0,
            entry_type TEXT DEFAULT 'revenue', description TEXT, date TEXT, exported INTEGER DEFAULT 0, created_at TEXT);
    """)
    c_ffl = c_led = 0
    for t in top:
        name = f"ASSET: {t['track']}"
        cur = conn.execute("SELECT id FROM contacts WHERE name=?", (name,)).fetchone()
        cid = cur["id"] if cur else conn.execute(
            "INSERT INTO contacts (name, role, ffl_status, notes, equity_score) VALUES (?,?,?,?,?)",
            (name, "catalog_asset", "vetted_top15",
             f"HPI {t['hpi']} (A{t['alpha']} SV{t['structural_velocity']}) {t['bpm']}BPM {t['key']}",
             t["hpi"]),
        ).lastrowid
        conn.execute(
            "INSERT INTO ffl_outreach (contact_id, message, equity_score) VALUES (?,?,?)",
            (cid, "Top-15 DSP-vetted catalog asset - ready for FFL distribution outreach.", t["hpi"]),
        )
        c_ffl += 1
        val = round(t["hpi"] * 100.0, 2)
        conn.execute(
            "INSERT INTO ledger (amount, entry_type, description, date) VALUES (?,?,?,?)",
            (val, "asset_value", f"DSP-vetted top-15: {t['track']} (HPI {t['hpi']})", date.today().isoformat()),
        )
        c_led += 1
    conn.commit()
    n = conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"]
    conn.close()
    return c_ffl, c_led, n


def send_email(subject, body):
    sys_path = str(_OMNI / "integrations")
    import sys as _sys
    _sys.path.insert(0, sys_path)
    try:
        from gmail_client import GmailClient
        gc = GmailClient()
        gc.authenticate()
        gc.send(TO, subject, body)
        return True
    except Exception as e:
        logging.error(f"Email failed: {e}")
        return False


def main():
    logging.info("Starting Hitmaker's Logic Local Audio Analysis Framework...")
    valid_extensions = ('.mp3', '.wav', '.m4a', '.flac')
    track_paths = [
        os.path.join(CATALOG_DIR, f) for f in os.listdir(CATALOG_DIR)
        if f.lower().endswith(valid_extensions)
    ]
    total = len(track_paths)
    logging.info(f"Discovered {total} tracks inside distribution catalog target path.")

    final_ledger = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_track = {executor.submit(process_single_track, p): p for p in track_paths}
        for future in concurrent.futures.as_completed(future_to_track):
            path = future_to_track[future]
            try:
                data = future.result()
                if data:
                    final_ledger.append(data)
                    with open(RESULTS_JSON, "w") as f:
                        json.dump(final_ledger, f, indent=4)
            except Exception as exc:
                logging.error(f"Worker fault for {Path(path).name}: {exc}")

    logging.info(f"Vetting complete. {len(final_ledger)} items written to {RESULTS_JSON}")
    summary, top = generate_summary(final_ledger)
    logging.info("\n" + summary)
    if top:
        c_ffl, c_led, n = ingest_ffl_ledger(top)
        logging.info(f"[auto-trigger] FFL: {c_ffl} | Ledger: {c_led} | contacts: {n}")
        ok = send_email("PMG Catalog Vet - Top 15 (DSP)", summary)
        logging.info(f"[email] Top 15 sent to {TO}: {ok}")


if __name__ == "__main__":
    main()
