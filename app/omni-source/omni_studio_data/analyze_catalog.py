#!/usr/bin/env python3
"""
Catalog Audio Analyzer — AI-powered analysis of billboard catalog tracks.
Uses local Ollama (gemma) for audio description and metadata extraction.
"""

import os
import sys
import json
import subprocess
import logging
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

from local_llm_connector import query_local_llm

load_dotenv(os.path.expanduser("~/Omni-Studio/config/.env"))
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('Catalog-Analyzer')

HOME = Path.home()
CATALOG_JSON = HOME / "catalog" / "catalog.json"
BILLBOARD_DIR = HOME / "PMG_Vault" / "Billboard_Catalog"
OUTPUT_DIR = HOME / "Omni-Studio" / "output" / "catalog_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# A&R persona for analysis
SYSTEM_PROMPT = """You are a multi-platinum A&R executive and music producer for Volt Records / PMG Management. 
You have an exceptional ear for hit records across all genres - Hip-Hop, R&B, Pop, Trap, and everything in between.

Analyze this track and provide:

1. **GENRE TAGS** - Primary and sub-genres (e.g., "Trap, Melodic Rap")
2. **MOOD/VIBE** - Emotional tone (e.g., "Confident, Aggressive", "Smooth, Romantic")
3. **PRODUCTION QUALITY** - Rate 1-10 with notes on mix, arrangement, sound design
4. **VOCAL DELIVERY** - Rate 1-10 with notes on tone, flow, emotion
5. **COMMERCIAL VIABILITY** - Rate 1-10 with target audience and playlist fit
6. **KEY ELEMENTS** - Notable hooks, beats, or moments
7. **SIMILAR ARTISTS** - 2-3 similar artists for comparison
8. **VERDICT** - PASS / DEVELOP / HIT POTENTIAL with explanation
9. **SCORE** - Overall score out of 10 (Alpha)
10. **VELOCITY** - Structural Velocity: hook density, dynamic range, and energy out of 10
11. **MODULARITY** - Market Modularity: how cleanly this track adapts to 15-second social clips out of 10

Be brutally honest. If it's a hit, say why. If it needs work, say what.
Always end with three lines:
SCORE: X/10
VELOCITY: X/10
MODULARITY: X/10"""


def get_ai_description(file_path: Path) -> dict:
    """Use local Ollama gemma to analyze audio features and generate description."""
    logger.info(f"Analyzing: {file_path.name}")
    
    file_ext = file_path.suffix.lower()
    file_size = file_path.stat().st_size
    file_size_mb = round(file_size / (1024 * 1024), 2)

    prompt = (
        f"TRACK TO VET: \"{file_path.stem}\" (format {file_ext}, {file_size_mb}MB)\n\n"
        "Apply the full A&R analysis rubric. For each section give a short note, "
        "then end your response with exactly:\n"
        "SCORE: X/10\n"
        "VELOCITY: X/10\n"
        "MODULARITY: X/10\n\n"
        "Rubric:\n"
        "1. GENRE TAGS - primary + sub-genres\n"
        "2. MOOD/VIBE - emotional tone\n"
        "3. PRODUCTION QUALITY - rate 1-10 with notes\n"
        "4. VOCAL DELIVERY - rate 1-10 with notes\n"
        "5. COMMERCIAL VIABILITY - rate 1-10, target audience + playlist fit\n"
        "6. KEY ELEMENTS - notable hooks/beats/moments\n"
        "7. SIMILAR ARTISTS - 2-3 comparisons\n"
        "8. VERDICT - PASS / DEVELOP / HIT POTENTIAL with explanation\n"
        "9. SCORE - overall 1-10 (Alpha — artistry, execution)\n"
        "10. VELOCITY - Structural Velocity 1-10 (hook density, dynamic range, energy)\n"
        "11. MODULARITY - Market Modularity 1-10 (fits 15s social clips, shareable moments)\n"
        "Be brutally honest."
    )
    result = query_local_llm(prompt, model="gemma")

    def parse_score(text: str, label: str) -> float:
        """Extract a score like 'SCORE: 8/10' or '**VELOCITY:** 7.5/10'."""
        if not text:
            return 0.0
        for variant in (f"**{label}:**", f"{label}:", f"**{label}**", label):
            if variant in text:
                after = text.split(variant)[-1].strip()
                num_str = "".join(ch for ch in after.split("/")[0] if ch.isdigit() or ch == ".")
                try:
                    return float(num_str) if num_str else 0.0
                except ValueError:
                    return 0.0
        return 0.0

    score = parse_score(result, "SCORE")
    velocity = parse_score(result, "VELOCITY")
    modularity = parse_score(result, "MODULARITY")

    # Fallback proxies if model didn't return structured scores
    if velocity == 0.0:
        velocity = score * 0.9
    if modularity == 0.0:
        modularity = score * 0.8

    return {
        "track": file_path.name,
        "path": str(file_path),
        "format": file_ext,
        "analysis": result,
        "score": score,
        "velocity_proxy": velocity,
        "mod_proxy": modularity,
        "analyzed_at": datetime.now().isoformat()
    }


def get_catalog_tracks() -> list[Path]:
    """Get all audio tracks from the billboard catalog."""
    tracks = []
    audio_exts = {".mp3", ".wav", ".aiff", ".m4a", ".aif", ".flac"}
    
    if not BILLBOARD_DIR.exists():
        logger.error(f"Billboard catalog not found: {BILLBOARD_DIR}")
        return tracks
    
    for entry in sorted(BILLBOARD_DIR.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.suffix.lower() in audio_exts:
            tracks.append(entry)
        elif entry.is_dir() and entry.name not in ("beats", "hoooks", "The Best In the World"):
            for f in entry.iterdir():
                if f.suffix.lower() in audio_exts:
                    tracks.append(f)
    
    return tracks


def analyze_batch(tracks: list[Path], max_workers: int = 2) -> list[dict]:
    """Analyze tracks in parallel with rate limiting."""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_ai_description, track): track for track in tracks}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            logger.info(f"Completed: {result['track']} (Score: {result['score']}/10)")
    
    return results


def parse_verdict(analysis: str) -> str:
    """Extract PASS / DEVELOP / HIT POTENTIAL verdict from analysis text."""
    if not analysis:
        return "UNKNOWN"
    up = analysis.upper()
    for v in ("HIT POTENTIAL", "HIT", "DEVELOP", "PASS"):
        if v in up:
            return v
    return "UNKNOWN"


def generate_report(results: list[dict]) -> dict:
    """Generate summary report from analysis results."""
    scored = [r for r in results if r["score"] > 0]
    for r in scored:
        r["verdict"] = parse_verdict(r.get("analysis", ""))

    report = {
        "catalog_name": "billboard catalog pmg",
        "generated_at": datetime.now().isoformat(),
        "total_analyzed": len(results),
        "successful_analyses": len(scored),
        "average_score": round(sum(r["score"] for r in scored) / len(scored), 2) if scored else 0,
        "top_tracks": sorted(scored, key=lambda x: x["score"], reverse=True)[:15],
        "hit_potential": [r for r in scored if r["score"] >= 8],
        "needs_development": [r for r in scored if 5 <= r["score"] < 8],
        "pass_tracks": [r for r in scored if r["score"] < 5],
        "results": results
    }

    return report


def main():
    logger.info("Starting Billboard Catalog PMG AI Analysis...")
    logger.info(f"Catalog: {BILLBOARD_DIR}")
    
    tracks = get_catalog_tracks()
    if not tracks:
        logger.error("No tracks found in catalog")
        sys.exit(1)
    
    logger.info(f"Found {len(tracks)} tracks to analyze")
    
    # Analyze all tracks
    results = analyze_batch(tracks, max_workers=2)
    
    # Generate report
    report = generate_report(results)
    
    # Save full report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"catalog_analysis_{timestamp}.json"
    output_file.write_text(json.dumps(report, indent=2))

    # Save HPI-ready input (for hitmaker_ranker.py)
    hpi_input = [
        {"track": r["track"], "score": r["score"],
         "velocity_proxy": r.get("velocity_proxy", r["score"] * 0.9),
         "mod_proxy": r.get("mod_proxy", r["score"] * 0.8)}
        for r in report["results"] if r["score"] > 0
    ]
    hpi_file = OUTPUT_DIR / f"catalog_analysis_{timestamp}_hpi_ready.json"
    hpi_file.write_text(json.dumps(hpi_input, indent=2))

    # Run hitmaker_ranker automatically
    try:
        ranker = Path(__file__).parent.parent / "Desktop/OMNI/hitmaker_ranker.py"
        if ranker.exists():
            subprocess.run(
                [sys.executable, str(ranker), "--input", str(hpi_file),
                 "--format", "json", "--top", "15"],
                cwd=str(ranker.parent), check=False)
    except Exception:
        pass

    # Print summary
    print("\n" + "=" * 70)
    print("BILLBOARD CATALOG PMG — AI ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Tracks Analyzed: {report['total_analyzed']}")
    print(f"Average Score: {report['average_score']}/10")
    print(f"\nTOP 15 TRACKS:")
    for i, track in enumerate(report["top_tracks"], 1):
        verdict = track.get("verdict", "UNKNOWN")
        print(f"  {i:2d}. {track['track'][:46]:46s} — {track['score']:4.1f}/10  [{verdict}]")
    
    if report["hit_potential"]:
        print(f"\n🔥 HIT POTENTIAL ({len(report['hit_potential'])} tracks):")
        for track in report["hit_potential"]:
            print(f"  • {track['track'][:55]} — {track['score']}/10")
    
    print(f"\nFull report: {output_file}")
    print(f"HPI input:   {hpi_file}")
    print(f"\nNext: python3 hitmaker_ranker.py --input '{hpi_file}' --format json --top 15")
    print("=" * 70)


if __name__ == "__main__":
    main()
