"""
Omni-Sampler Engine — Universal DAW sampler kit builder.

Creates instrument kits from local samples + Google Drive and exports them to
formats every DAW can load:
- SFZ (universal open sampler format)
- Folder + JSON metadata
- Optional: direct upload to Google Drive
"""
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from sample_library import get_db, get_sample, search_samples
from config import BASE

EXPORT_DIR = BASE / "data" / "sampler-exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# MIDI note mapping for drum samples (General MIDI drums)
DRUM_MAP = {
    "kick": 36, "kik": 36, "bd": 36,
    "snare": 38, "sn": 38, "sd": 38, "clap": 39,
    "hihat": 42, "hat": 42, "hh": 42, "closed": 42,
    "openhat": 46, "oh": 46, "crash": 49, "ride": 51,
    "tom": 45, "lowtom": 41, "midtom": 47, "hightom": 50,
    "perc": 37, "percussion": 37, "shaker": 82, "tamb": 54,
    "claves": 75, "cowbell": 56, "rim": 37,
    "bass": 36, "sub": 35,
}

KEY_NAME_TO_MIDI = {
    "C": 60, "C#": 61, "D": 62, "D#": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "G#": 68, "A": 69, "A#": 70, "B": 71,
}


def _parse_key(key_full: str) -> int:
    """Convert a key like 'C major' / 'A# minor' to a MIDI note number."""
    if not key_full:
        return 60
    key_full = key_full.strip()
    root = key_full.split()[0].upper()
    # Normalize flats to sharps
    root = root.replace("DB", "C#").replace("EB", "D#").replace("GB", "F#")
    root = root.replace("AB", "G#").replace("BB", "A#")
    return KEY_NAME_TO_MIDI.get(root, 60)


def _guess_drum_note(filename: str) -> int:
    """Infer General MIDI drum note from filename."""
    name = Path(filename).stem.lower()
    for keyword, note in DRUM_MAP.items():
        if keyword in name:
            return note
    return 60  # Default to C3 if unknown


def _safe_filename(name: str) -> str:
    """Make a filesystem-safe name."""
    keep = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    return "".join(c if c in keep else "-" for c in name.lower().strip()).strip("-")


async def create_kit(name: str, description: str, layout_type: str, sample_ids: List[int]) -> int:
    """Create a new sampler kit from a list of sample IDs."""
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO kits (name, description, layout_type) VALUES (?, ?, ?)",
        (name, description, layout_type)
    )
    kit_id = cursor.lastrowid

    for idx, sample_id in enumerate(sample_ids):
        sample = await get_sample(sample_id)
        if not sample:
            continue

        if layout_type == "drum":
            midi_note = _guess_drum_note(sample["filename"])
            lo_note = midi_note
            hi_note = midi_note
            pitch_center = midi_note
        else:  # chromatic / melodic
            midi_note = 60 + idx  # Spread chromatically upward from C3
            lo_note = midi_note
            hi_note = midi_note
            pitch_center = _parse_key(sample.get("key_full", ""))

        await db.execute(
            """INSERT INTO kit_samples
               (kit_id, sample_id, midi_note, lo_note, hi_note, pitch_center, root_key)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (kit_id, sample_id, midi_note, lo_note, hi_note, pitch_center, sample.get("key", ""))
        )

    await db.commit()
    await db.close()
    return kit_id


async def get_kits() -> List[dict]:
    """List all kits with sample count."""
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT k.*, COUNT(ks.id) as sample_count
           FROM kits k
           LEFT JOIN kit_samples ks ON k.id = ks.kit_id
           GROUP BY k.id
           ORDER BY k.created_at DESC"""
    )
    await db.close()
    return [dict(r) for r in rows]


async def get_kit(kit_id: int) -> Optional[dict]:
    """Get a single kit with all mapped samples."""
    db = await get_db()
    kit_rows = await db.execute_fetchall("SELECT * FROM kits WHERE id=?", (kit_id,))
    if not kit_rows:
        await db.close()
        return None
    kit = dict(kit_rows[0])

    sample_rows = await db.execute_fetchall(
        """SELECT ks.*, s.filename, s.path, s.key_full, s.sample_type, s.duration
           FROM kit_samples ks
           JOIN samples s ON ks.sample_id = s.id
           WHERE ks.kit_id=?
           ORDER BY ks.midi_note""",
        (kit_id,)
    )
    kit["samples"] = [dict(r) for r in sample_rows]
    await db.close()
    return kit


async def delete_kit(kit_id: int):
    """Delete a kit and its mappings."""
    db = await get_db()
    await db.execute("DELETE FROM kits WHERE id=?", (kit_id,))
    await db.commit()
    await db.close()


def build_sfz(kit: dict) -> str:
    """Render SFZ text for a kit."""
    lines = [
        "// Omni-Sampler SFZ export",
        f"// Kit: {kit['name']}",
        f"// Created: {datetime.now().isoformat()}",
        "<control>",
        "default_path=samples/",
        "<group>",
    ]

    for s in kit.get("samples", []):
        sample_name = _safe_filename(s["filename"])
        # Use original extension
        ext = Path(s["filename"]).suffix.lower() or ".wav"
        sample_name = f"{sample_name}{ext}"
        lines.append(
            f"  <region> sample={sample_name} "
            f"key={s['midi_note']} lokey={s['lo_note']} hikey={s['hi_note']} "
            f"pitch_keycenter={s['pitch_center']} "
            f"lovel={s.get('velocity_lo', 0)} hivel={s.get('velocity_hi', 127)} "
            f"volume={s.get('volume_db', 0.0)}"
        )
    return "\n".join(lines)


async def export_kit(kit_id: int, fmt: str = "sfz") -> dict:
    """Export a kit to a folder/zip. Returns export metadata."""
    kit = await get_kit(kit_id)
    if not kit:
        raise ValueError(f"Kit {kit_id} not found")

    safe_name = _safe_filename(kit["name"])
    export_root = EXPORT_DIR / f"{safe_name}-{kit_id}"
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)

    samples_dir = export_root / "samples"
    samples_dir.mkdir()

    copied = []
    for s in kit.get("samples", []):
        src = Path(s["path"])
        if not src.exists():
            continue
        dest_name = _safe_filename(s["filename"]) + src.suffix.lower()
        dest = samples_dir / dest_name
        shutil.copy2(src, dest)
        copied.append(dest_name)

    if fmt == "sfz":
        sfz_text = build_sfz(kit)
        sfz_path = export_root / f"{safe_name}.sfz"
        sfz_path.write_text(sfz_text, encoding="utf-8")

    # JSON metadata
    meta = {
        "name": kit["name"],
        "description": kit["description"],
        "layout_type": kit["layout_type"],
        "created_at": kit["created_at"],
        "sample_count": len(kit.get("samples", [])),
        "format": fmt,
    }
    (export_root / "kit.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Zip it up
    zip_path = EXPORT_DIR / f"{safe_name}-{kit_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in export_root.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(EXPORT_DIR))

    return {
        "kit_id": kit_id,
        "format": fmt,
        "folder": str(export_root),
        "zip": str(zip_path),
        "samples_copied": len(copied),
    }


async def update_kit_drive_url(kit_id: int, url: str):
    """Record a Google Drive share URL for a kit export."""
    db = await get_db()
    await db.execute(
        "UPDATE kits SET drive_url=?, updated_at=datetime('now') WHERE id=?",
        (url, kit_id)
    )
    await db.commit()
    await db.close()
