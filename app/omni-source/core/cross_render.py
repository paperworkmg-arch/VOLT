"""
Cross-Render Pipeline — text → music → stems → sampler kit.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

STUDIO_DIR = Path(__file__).parent.parent
DB_PATH = STUDIO_DIR / "data" / "cross_render.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
RENDER_DIR = STUDIO_DIR / "data" / "renders"
RENDER_DIR.mkdir(parents=True, exist_ok=True)


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS renders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            stages TEXT DEFAULT '{}',
            kit_id INTEGER,
            error TEXT
        );
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_renders(limit: int = 20) -> list[dict]:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM renders ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_render(render_id: int) -> dict | None:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM renders WHERE id=?", (render_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def create_render(prompt: str) -> int:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "INSERT INTO renders (prompt, status, stages) VALUES (?, 'pending', ?)",
        (prompt, json.dumps({}))
    )
    render_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return render_id


async def run_render(render_id: int):
    """Execute cross-render pipeline."""
    import sys
    sys.path.insert(0, str(STUDIO_DIR / "dashboard"))
    from sample_library import upsert_sample
    from sampler_engine import create_kit, export_kit

    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM renders WHERE id=?", (render_id,)).fetchone()
    if not row:
        conn.close()
        return "not_found"
    render = _row_to_dict(row)
    prompt = render["prompt"]

    def update(**kwargs):
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [render_id]
        conn.execute(f"UPDATE renders SET {sets}, updated_at=datetime('now') WHERE id=?", vals)
        conn.commit()

    stages = {
        "generate": {"status": "running", "output": "", "artifact": ""},
        "stems": {"status": "pending", "output": "", "artifact": ""},
        "analyze": {"status": "pending", "output": "", "artifact": ""},
        "kit": {"status": "pending", "output": "", "artifact": ""},
        "export": {"status": "pending", "output": "", "artifact": ""},
    }
    update(status="running", stages=json.dumps(stages))

    try:
        render_dir = RENDER_DIR / f"render_{render_id}"
        render_dir.mkdir(parents=True, exist_ok=True)

        # Generate placeholder audio
        audio_file = render_dir / "generated.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
        stages["generate"].update({"status": "success", "artifact": str(audio_file), "output": "Audio generated (placeholder)"})
        update(stages=json.dumps(stages))

        # Separate stems (placeholder)
        stems_dir = render_dir / "stems"
        stems_dir.mkdir(exist_ok=True)
        for stem in ["vocals", "drums", "bass", "other"]:
            (stems_dir / f"{stem}.wav").write_bytes(b"RIFF" + b"\x00" * 100)
        stages["stems"].update({"status": "success", "artifact": str(stems_dir), "output": "Stems separated (placeholder)"})
        update(stages=json.dumps(stages))

        # Catalog samples
        sample_ids = []
        for stem_path in sorted(stems_dir.glob("*.wav")):
            sid = await upsert_sample({
                "path": str(stem_path), "filename": stem_path.name,
                "directory": str(stems_dir), "extension": ".wav",
                "size_bytes": stem_path.stat().st_size,
                "size_mb": round(stem_path.stat().st_size / (1024 * 1024), 4),
                "sample_type": "full-track", "analyzed": 0,
            })
            sample_ids.append(sid)
        stages["analyze"].update({"status": "success", "output": f"Cataloged {len(sample_ids)} stems"})
        update(stages=json.dumps(stages))

        # Build kit
        layout = "drum" if "drum" in prompt.lower() else "chromatic"
        kit_id = await create_kit(f"Render {render_id} Kit", f"From: {prompt[:80]}", layout, sample_ids)
        stages["kit"].update({"status": "success", "artifact": str(kit_id), "output": f"Created kit {kit_id}"})
        update(kit_id=kit_id, stages=json.dumps(stages))

        # Export SFZ
        result = await export_kit(kit_id, "sfz")
        stages["export"].update({"status": "success", "artifact": result["zip"], "output": f"Exported {result['samples_copied']} samples"})
        update(stages=json.dumps(stages))

        final = "success"
    except Exception as exc:
        update(error=str(exc))
        final = "failed"

    update(status=final)
    conn.close()
    return final
