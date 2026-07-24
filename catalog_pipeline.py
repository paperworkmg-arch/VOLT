#!/usr/bin/env python3
"""Catalog Intelligence Pipeline v1 — Omni-Studio asset inventory."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

HOME = Path.home()
CATALOG_DIR = HOME / "catalog"
OUTPUT = CATALOG_DIR / "catalog.json"
LOGIC_DIR = HOME / "Music/Audio Music Apps/Logic"
LOGIC_DIR_2 = HOME / "Music/Logic"
PT_DIR = HOME / "Music/pro toolls 2026"
LUNA_DIR = HOME / "Music/LUNA Sessions"
BILLBOARD_DIR = HOME / "PMG_Vault" / "Billboard_Catalog"


def size_fmt(path: Path) -> str:
    try:
        result = subprocess.run(
            ["du", "-sh", str(path)],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.split("\t")[0] if result.stdout else "?"
    except Exception:
        return "?"


def file_mtime(path: Path) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).isoformat()
    except Exception:
        return "?"


def scan_logic() -> list[dict[str, Any]]:
    projects = []
    for logic_dir in [LOGIC_DIR, LOGIC_DIR_2]:
        if not logic_dir.exists():
            continue
        for entry in sorted(logic_dir.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                logicx_files = list(entry.glob("*.logicx"))
                bounces_dir = entry / "Bounces"
                stems = list(entry.glob("*stem*")) + list(entry.glob("*Stem*"))
                projects.append({
                    "type": "logic_project",
                    "name": entry.name,
                    "path": str(entry),
                    "has_logicx": len(logicx_files) > 0,
                    "logicx_files": [f.name for f in logicx_files],
                    "has_bounces": bounces_dir.exists(),
                    "bounces_size": size_fmt(bounces_dir) if bounces_dir.exists() else "0B",
                    "stems_count": len(stems),
                    "last_modified": file_mtime(entry),
                    "total_size": size_fmt(entry),
                })
            elif entry.suffix == ".logicx" or (entry.is_dir() and entry.suffix == ".logicx"):
                projects.append({
                    "type": "logicx_loose",
                    "name": entry.stem,
                    "path": str(entry),
                    "last_modified": file_mtime(entry),
                })
    return projects


def scan_protools() -> list[dict[str, Any]]:
    projects = []
    if not PT_DIR.exists():
        return projects
    for entry in sorted(PT_DIR.iterdir()):
        if entry.is_dir():
            ptx_files = list(entry.rglob("*.ptx"))
            if ptx_files:
                projects.append({
                    "type": "protools_session",
                    "name": entry.name,
                    "path": str(entry),
                    "session_count": len(ptx_files),
                    "session_files": [f.name for f in ptx_files[:5]],
                    "last_modified": file_mtime(entry),
                    "total_size": size_fmt(entry),
                })
    return projects


def scan_luna() -> list[dict[str, Any]]:
    projects = []
    if not LUNA_DIR.exists():
        return projects
    for entry in sorted(LUNA_DIR.iterdir()):
        if entry.suffix == ".luna" or entry.is_dir():
            projects.append({
                "type": "luna_project",
                "name": entry.stem if entry.suffix == ".luna" else entry.name,
                "path": str(entry),
                "last_modified": file_mtime(entry),
                "total_size": size_fmt(entry),
            })
    return projects


def scan_billboard() -> list[dict[str, Any]]:
    tracks = []
    if not BILLBOARD_DIR.exists():
        return tracks
    audio_exts = {".mp3", ".wav", ".aiff", ".m4a", ".aif", ".flac"}
    for entry in sorted(BILLBOARD_DIR.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.suffix.lower() in audio_exts:
            tracks.append({
                "type": "billboard_track",
                "name": entry.stem,
                "path": str(entry),
                "format": entry.suffix.lower(),
                "size": size_fmt(entry),
                "last_modified": file_mtime(entry),
            })
        elif entry.is_dir() and entry.name not in ("beats", "hoooks", "The Best In the World"):
            sub_files = list(entry.iterdir())
            sub_audio = [f for f in sub_files if f.suffix.lower() in audio_exts]
            for f in sorted(sub_audio):
                tracks.append({
                    "type": "billboard_track",
                    "name": f.stem,
                    "path": str(f),
                    "format": f.suffix.lower(),
                    "size": size_fmt(f),
                    "last_modified": file_mtime(f),
                    "subfolder": entry.name,
                })
    return tracks


def scan_bounces(all_projects: list[dict]) -> list[dict]:
    bounces = []
    for p in all_projects:
        if p.get("has_bounces"):
            bounces_dir = Path(p["path"]) / "Bounces"
            files = sorted(bounces_dir.iterdir()) if bounces_dir.exists() else []
            wav_files = [f for f in files if f.suffix.lower() in (".wav", ".aiff", ".mp3")]
            if wav_files:
                total_dur = 0
                for w in wav_files:
                    try:
                        total_dur += os.path.getsize(w)
                    except Exception:
                        pass
                bounces.append({
                    "project": p["name"],
                    "bounce_path": str(bounces_dir),
                    "total_bounces": len(wav_files),
                    "total_bytes": total_dur,
                })
    return bounces


def scan_stems() -> list[dict]:
    stems = []
    for d in [
        LOGIC_DIR / "wont od thaty stems",
        LOGIC_DIR / "nw stems chasing",
        LOGIC_DIR / "stems abyss",
        LOGIC_DIR / "new stems 130",
        LOGIC_DIR / "STEMS STALLION",
        LOGIC_DIR / "stems ye",
    ]:
        if d.exists():
            files = list(d.iterdir()) if d.is_dir() else []
            wav = [f for f in files if f.suffix.lower() in (".wav", ".aiff")]
            stems.append({
                "name": d.name,
                "path": str(d),
                "file_count": len(wav),
                "size": size_fmt(d),
            })
    return stems


def main() -> None:
    CATALOG_DIR.mkdir(exist_ok=True)

    logic = scan_logic()
    protools = scan_protools()
    luna = scan_luna()
    billboard = scan_billboard()
    bounces = scan_bounces(logic)
    stems = scan_stems()

    catalog = {
        "catalog_name": "billboard catalog pmg",
        "generated_at": datetime.now().isoformat(),
        "hostname": subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip(),
        "summary": {
            "logic_projects": len([p for p in logic if p["type"] == "logic_project"]),
            "logicx_loose": len([p for p in logic if p["type"] == "logicx_loose"]),
            "protools_sessions": len(protools),
            "luna_projects": len(luna),
            "billboard_tracks": len(billboard),
            "total_projects": len(logic) + len(protools) + len(luna),
            "bounce_dirs": len(bounces),
            "total_bounce_files": sum(b["total_bounces"] for b in bounces),
            "stem_folders": len(stems),
            "estimated_bounce_size_gb": round(sum(b["total_bytes"] for b in bounces) / 1e9, 1),
        },
        "logic_projects": logic,
        "protools_sessions": protools,
        "luna_projects": luna,
        "billboard_catalog": billboard,
        "bounces": bounces,
        "stems": stems,
    }

    OUTPUT.write_text(json.dumps(catalog, indent=2))
    print(f"Catalog written to {OUTPUT}")
    print(json.dumps(catalog["summary"], indent=2))


if __name__ == "__main__":
    main()
