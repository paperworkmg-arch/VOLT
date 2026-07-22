"""
Sample Scanner — scans all audio files on the system, extracts key/tempo metadata.
Stores everything in a SQLite database for instant search.
"""
import os
import json
import hashlib
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("sample_scanner")

# Directories to scan
SCAN_DIRS = [
    Path.home() / "Music" / "Logic",
    Path.home() / "Music" / "Logic" / "Bounces",
    Path.home() / "Music" / "Audio Music Apps",
    Path.home() / "Music" / "Ableton",
    Path.home() / "Music" / "Loose Imports",
    Path.home() / "Omni-Studio" / "Audio",
    Path.home() / "Omni-Studio" / "omni_studio_data" / "submissions",
    Path.home() / "Desktop" / "all files",
    Path.home() / "Downloads" / "WMG",
    Path.home() / "Downloads",
]

# Directories to SKIP (large system folders, non-audio)
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".Trash",
    "Logic Pro Library.bundle",  # Apple's own library, skip deep scan
    "Soundz",  # Large Splice packs — skip for song catalog
    "sampler-exports",
}

# Audio file extensions
AUDIO_EXTENSIONS = {
    ".wav", ".aif", ".aiff", ".mp3", ".flac",
    ".m4a", ".caf", ".ogg", ".opus", ".wma",
}

# Krumhansl-Schmuckler key profiles (lazy-load numpy at runtime)
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key_and_tempo(filepath: str) -> dict:
    """Detect musical key and tempo of an audio file using librosa."""
    import librosa
    import numpy as np
    try:
        y, sr = librosa.load(filepath, sr=22050, mono=True, duration=30)
        if len(y) < 1024:
            return {"key": "", "mode": "", "key_full": "Unknown", "tempo": 0.0}

        # Tempo detection
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, '__len__'):
            tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
        else:
            tempo = float(tempo)

        # Key detection via chromagram + cosine similarity
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Normalize
        chroma_norm = np.linalg.norm(chroma_mean)
        if chroma_norm > 0:
            chroma_mean = chroma_mean / chroma_norm

        # Krumhansl-Schmuckler key profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Normalize profiles
        major_profile = major_profile / np.linalg.norm(major_profile)
        minor_profile = minor_profile / np.linalg.norm(minor_profile)

        # Try all 12 transpositions via circular correlation
        best_score = -2
        best_key = 0
        best_mode = "major"
        
        for shift in range(12):
            shifted = np.roll(chroma_mean, -shift)
            major_corr = np.dot(shifted, major_profile)
            minor_corr = np.dot(shifted, minor_profile)
            
            if major_corr > best_score:
                best_score = major_corr
                best_key = shift
                best_mode = "major"
            if minor_corr > best_score:
                best_score = minor_corr
                best_key = shift
                best_mode = "minor"

        key = KEY_NAMES[best_key]

        return {
            "key": key,
            "mode": best_mode,
            "key_full": f"{key} {best_mode}",
            "tempo": round(tempo, 1),
        }
    except Exception as e:
        logger.debug(f"Key/tempo detection failed for {filepath}: {e}")
        return {"key": "", "mode": "", "key_full": "Unknown", "tempo": 0.0}


def get_audio_duration(filepath: str) -> float:
    """Get audio duration in seconds."""
    import librosa
    try:
        info = librosa.get_duration(path=filepath)
        return round(float(info), 2)
    except:
        return 0.0


def get_file_hash(filepath: str) -> str:
    """Quick hash based on path + size (not full content hash for speed)."""
    size = os.path.getsize(filepath)
    return hashlib.md5(f"{filepath}:{size}".encode()).hexdigest()


def classify_sample(filepath: str) -> str:
    """Classify sample type based on filename and directory context."""
    name = Path(filepath).stem.lower().replace("_", " ").replace("-", " ")
    parent = str(Path(filepath).parent).lower()

    # One-shot detection
    if any(kw in name for kw in ["one shot", "oneshot", "one-shot", "hit", "stab", "snap", "clap"]):
        return "one-shot"

    # Loop detection
    if any(kw in name for kw in ["loop", "beat", "pattern", "groove"]):
        return "loop"

    # From directory context
    if "drum" in parent:
        return "drum" if "loop" in name or "beat" in name else "one-shot"
    if "loop" in parent:
        return "loop"
    if "bounces" in parent or "bounce" in parent:
        return "export"
    if ".logicx" in parent:
        return "project-sample"

    # Try to infer from duration
    try:
        dur = get_audio_duration(filepath)
        if dur < 2.0:
            return "one-shot"
        elif dur < 8.0:
            return "loop"
        else:
            return "full-track"
    except:
        return "unknown"


def scan_single_file(filepath: str) -> dict | None:
    """Scan a single audio file and return metadata."""
    try:
        path = Path(filepath)
        stat = path.stat()

        return {
            "path": str(path),
            "filename": path.name,
            "directory": str(path.parent),
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "file_hash": get_file_hash(filepath),
            "sample_type": classify_sample(filepath),
            "key": "",
            "mode": "",
            "key_full": "Analyzing...",
            "tempo": 0.0,
            "duration": 0.0,
            "analyzed": False,
        }
    except Exception as e:
        logger.error(f"Error scanning {filepath}: {e}")
        return None


def scan_all_audio(limit: int = 0) -> list[dict]:
    """Scan all audio files on the system. Returns list of metadata dicts."""
    files_found = []
    scanned = set()

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        logger.info(f"Scanning: {scan_dir}")

        for root, dirs, files in os.walk(scan_dir):
            # Skip system directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            for f in files:
                if limit and len(files_found) >= limit:
                    return files_found

                filepath = os.path.join(root, f)
                if filepath in scanned:
                    continue
                scanned.add(filepath)

                ext = Path(f).suffix.lower()
                if ext not in AUDIO_EXTENSIONS:
                    continue

                meta = scan_single_file(filepath)
                if meta:
                    files_found.append(meta)

    logger.info(f"Found {len(files_found)} audio files")
    return files_found


async def analyze_audio_metadata(files: list[dict], progress_callback=None) -> list[dict]:
    """Analyze key/tempo for all scanned files. Runs in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    total = len(files)
    analyzed = 0

    def analyze_one(f):
        if f["analyzed"]:
            return f
        try:
            result = detect_key_and_tempo(f["path"])
            f["key"] = result["key"]
            f["mode"] = result["mode"]
            f["key_full"] = result["key_full"]
            f["tempo"] = result["tempo"]
            f["duration"] = get_audio_duration(f["path"])
            f["analyzed"] = True
        except Exception as e:
            logger.debug(f"Analysis failed for {f['filename']}: {e}")
            f["key_full"] = "Unknown"
            f["analyzed"] = True  # Mark as analyzed so we don't retry
        return f

    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = []
        for f in files:
            if not f.get("analyzed"):
                tasks.append(loop.run_in_executor(pool, analyze_one, f))

        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            analyzed += 1
            if progress_callback and analyzed % 10 == 0:
                await progress_callback(analyzed, total, result.get("filename", ""))

    return files


# Quick scan: just find files without deep analysis
async def quick_scan(limit: int = 0) -> list[dict]:
    """Quick scan — finds all audio files without key/tempo analysis."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = await loop.run_in_executor(pool, scan_all_audio, limit)
    return files


# Full scan: find + analyze
async def full_scan(progress_callback=None) -> list[dict]:
    """Full scan — finds all audio files AND analyzes key/tempo."""
    files = await quick_scan()
    if progress_callback:
        await progress_callback(0, len(files), "Starting analysis...")
    files = await analyze_audio_metadata(files, progress_callback)
    return files
