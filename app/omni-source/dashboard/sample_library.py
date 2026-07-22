"""
Sample Library — SQLite database for sample search with key/tempo/genre filtering.
Scans audio files, stores metadata, and provides instant search.
"""
import aiosqlite
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "samples.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _ensure_tables():
    """Create tables synchronously at import time."""
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            directory TEXT,
            extension TEXT,
            size_bytes INTEGER DEFAULT 0,
            size_mb REAL DEFAULT 0.0,
            modified_at TEXT,
            file_hash TEXT,
            sample_type TEXT DEFAULT 'unknown',
            key TEXT,
            mode TEXT,
            key_full TEXT,
            tempo REAL DEFAULT 0.0,
            duration REAL DEFAULT 0.0,
            analyzed INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            drive_id TEXT,
            drive_url TEXT,
            synced_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_samples_key ON samples(key);
        CREATE INDEX IF NOT EXISTS idx_samples_tempo ON samples(tempo);
        CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(sample_type);
        CREATE INDEX IF NOT EXISTS idx_samples_directory ON samples(directory);
        CREATE INDEX IF NOT EXISTS idx_samples_filename ON samples(filename);
        CREATE INDEX IF NOT EXISTS idx_samples_analyzed ON samples(analyzed);
        CREATE TABLE IF NOT EXISTS scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            files_found INTEGER DEFAULT 0,
            files_analyzed INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0.0,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS drive_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER,
            drive_id TEXT,
            drive_url TEXT,
            folder TEXT,
            synced_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sample_id) REFERENCES samples(id)
        );

        CREATE TABLE IF NOT EXISTS kits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            layout_type TEXT DEFAULT 'drum',
            export_path TEXT,
            drive_url TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kit_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_id INTEGER,
            sample_id INTEGER,
            midi_note INTEGER,
            lo_note INTEGER,
            hi_note INTEGER,
            pitch_center INTEGER,
            velocity_lo INTEGER DEFAULT 0,
            velocity_hi INTEGER DEFAULT 127,
            root_key TEXT,
            fine_tune INTEGER DEFAULT 0,
            volume_db REAL DEFAULT 0.0,
            FOREIGN KEY (kit_id) REFERENCES kits(id) ON DELETE CASCADE,
            FOREIGN KEY (sample_id) REFERENCES samples(id)
        );
    """)
    conn.commit()
    conn.close()

_ensure_tables()


async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_sample_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            directory TEXT,
            extension TEXT,
            size_bytes INTEGER DEFAULT 0,
            size_mb REAL DEFAULT 0.0,
            modified_at TEXT,
            file_hash TEXT,
            sample_type TEXT DEFAULT 'unknown',
            key TEXT,
            mode TEXT,
            key_full TEXT,
            tempo REAL DEFAULT 0.0,
            duration REAL DEFAULT 0.0,
            analyzed INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            drive_id TEXT,
            drive_url TEXT,
            synced_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_samples_key ON samples(key);
        CREATE INDEX IF NOT EXISTS idx_samples_tempo ON samples(tempo);
        CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(sample_type);
        CREATE INDEX IF NOT EXISTS idx_samples_directory ON samples(directory);
        CREATE INDEX IF NOT EXISTS idx_samples_filename ON samples(filename);
        CREATE INDEX IF NOT EXISTS idx_samples_analyzed ON samples(analyzed);

        CREATE TABLE IF NOT EXISTS scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            files_found INTEGER DEFAULT 0,
            files_analyzed INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0.0,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS drive_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER,
            drive_id TEXT,
            drive_url TEXT,
            folder TEXT,
            synced_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (sample_id) REFERENCES samples(id)
        );

        CREATE TABLE IF NOT EXISTS kits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            layout_type TEXT DEFAULT 'drum',
            export_path TEXT,
            drive_url TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kit_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_id INTEGER,
            sample_id INTEGER,
            midi_note INTEGER,
            lo_note INTEGER,
            hi_note INTEGER,
            pitch_center INTEGER,
            velocity_lo INTEGER DEFAULT 0,
            velocity_hi INTEGER DEFAULT 127,
            root_key TEXT,
            fine_tune INTEGER DEFAULT 0,
            volume_db REAL DEFAULT 0.0,
            FOREIGN KEY (kit_id) REFERENCES kits(id) ON DELETE CASCADE,
            FOREIGN KEY (sample_id) REFERENCES samples(id)
        );
    """)
    await db.commit()
    await db.close()


async def upsert_sample(meta: dict) -> int:
    db = await get_db()
    await db.execute("""
        INSERT INTO samples (path, filename, directory, extension, size_bytes, size_mb,
            modified_at, file_hash, sample_type, key, mode, key_full, tempo, duration, analyzed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            size_bytes=excluded.size_bytes, size_mb=excluded.size_mb,
            modified_at=excluded.modified_at, file_hash=excluded.file_hash,
            sample_type=excluded.sample_type, key=excluded.key, mode=excluded.mode,
            key_full=excluded.key_full, tempo=excluded.tempo, duration=excluded.duration,
            analyzed=excluded.analyzed, updated_at=datetime('now')
    """, (
        meta.get("path"), meta.get("filename"), meta.get("directory"),
        meta.get("extension"), meta.get("size_bytes", 0), meta.get("size_mb", 0.0),
        meta.get("modified_at"), meta.get("file_hash"), meta.get("sample_type", "unknown"),
        meta.get("key", ""), meta.get("mode", ""), meta.get("key_full", "Unknown"),
        meta.get("tempo", 0.0), meta.get("duration", 0.0), meta.get("analyzed", 0)
    ))
    await db.commit()
    row = await db.execute_fetchall("SELECT id FROM samples WHERE path=?", (meta.get("path"),))
    sample_id = row[0][0] if row else 0
    await db.close()
    return sample_id


async def bulk_upsert_samples(files: list[dict]) -> int:
    db = await get_db()
    count = 0
    for meta in files:
        await db.execute("""
            INSERT INTO samples (path, filename, directory, extension, size_bytes, size_mb,
                modified_at, file_hash, sample_type, key, mode, key_full, tempo, duration, analyzed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size_bytes=excluded.size_bytes, size_mb=excluded.size_mb,
                modified_at=excluded.modified_at, file_hash=excluded.file_hash,
                sample_type=excluded.sample_type, key=excluded.key, mode=excluded.mode,
                key_full=excluded.key_full, tempo=excluded.tempo, duration=excluded.duration,
                analyzed=excluded.analyzed, updated_at=datetime('now')
        """, (
            meta.get("path"), meta.get("filename"), meta.get("directory"),
            meta.get("extension"), meta.get("size_bytes", 0), meta.get("size_mb", 0.0),
            meta.get("modified_at"), meta.get("file_hash"), meta.get("sample_type", "unknown"),
            meta.get("key", ""), meta.get("mode", ""), meta.get("key_full", "Unknown"),
            meta.get("tempo", 0.0), meta.get("duration", 0.0), meta.get("analyzed", 0)
        ))
        count += 1
    await db.commit()
    await db.close()
    return count


async def search_samples(
    q: str = "",
    key: str = "",
    tempo_min: float = 0,
    tempo_max: float = 999,
    sample_type: str = "",
    directory: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    db = await get_db()
    conditions = []
    params = []

    if q:
        conditions.append("(filename LIKE ? OR tags LIKE ? OR notes LIKE ?)")
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    if key:
        conditions.append("key = ?")
        params.append(key)

    if tempo_min > 0:
        conditions.append("tempo >= ?")
        params.append(tempo_min)

    if tempo_max < 999:
        conditions.append("tempo <= ?")
        params.append(tempo_max)

    if sample_type:
        conditions.append("sample_type = ?")
        params.append(sample_type)

    if directory:
        conditions.append("directory LIKE ?")
        params.append(f"%{directory}%")

    where = " AND ".join(conditions) if conditions else "1=1"

    count_row = await db.execute_fetchall(f"SELECT COUNT(*) FROM samples WHERE {where}", params)
    total = count_row[0][0] if count_row else 0

    rows = await db.execute_fetchall(
        f"SELECT * FROM samples WHERE {where} ORDER BY filename LIMIT ? OFFSET ?",
        params + [limit, offset]
    )
    await db.close()
    return {"samples": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


async def get_sample(sample_id: int) -> dict | None:
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM samples WHERE id=?", (sample_id,))
    await db.close()
    return dict(rows[0]) if rows else None


async def update_sample_tags(sample_id: int, tags: list[str]):
    db = await get_db()
    await db.execute("UPDATE samples SET tags=?, updated_at=datetime('now') WHERE id=?",
                     (json.dumps(tags), sample_id))
    await db.commit(); await db.close()


async def update_sample_notes(sample_id: int, notes: str):
    db = await get_db()
    await db.execute("UPDATE samples SET notes=?, updated_at=datetime('now') WHERE id=?",
                     (notes, sample_id))
    await db.commit(); await db.close()


async def get_sample_stats() -> dict:
    db = await get_db()
    stats = {}

    row = await db.execute_fetchall("SELECT COUNT(*) FROM samples")
    stats["total_samples"] = row[0][0]

    row = await db.execute_fetchall("SELECT COUNT(*) FROM samples WHERE analyzed=1")
    stats["analyzed"] = row[0][0]

    row = await db.execute_fetchall("SELECT COUNT(*) FROM samples WHERE analyzed=0")
    stats["unanalyzed"] = row[0][0]

    rows = await db.execute_fetchall(
        "SELECT key, COUNT(*) as c FROM samples WHERE key != '' AND analyzed=1 GROUP BY key ORDER BY c DESC")
    stats["by_key"] = [{"key": r["key"], "count": r["c"]} for r in rows]

    rows = await db.execute_fetchall(
        "SELECT sample_type, COUNT(*) as c FROM samples GROUP BY sample_type ORDER BY c DESC")
    stats["by_type"] = [{"type": r["sample_type"], "count": r["c"]} for r in rows]

    rows = await db.execute_fetchall(
        "SELECT directory, COUNT(*) as c FROM samples GROUP BY directory ORDER BY c DESC LIMIT 10")
    stats["by_directory"] = [{"dir": r["directory"], "count": r["c"]} for r in rows]

    row = await db.execute_fetchall("SELECT SUM(size_mb), AVG(duration) FROM samples")
    stats["total_size_mb"] = round(row[0][0] or 0, 1)
    stats["avg_duration"] = round(row[0][1] or 0, 1)

    tempo_rows = await db.execute_fetchall(
        "SELECT tempo FROM samples WHERE tempo > 0 AND analyzed=1")
    tempos = [r[0] for r in tempo_rows]
    if tempos:
        stats["tempo_range"] = [round(min(tempos)), round(max(tempos))]
        stats["avg_tempo"] = round(sum(tempos) / len(tempos))
    else:
        stats["tempo_range"] = [0, 0]
        stats["avg_tempo"] = 0

    await db.close()
    return stats


async def start_scan() -> int:
    db = await get_db()
    cursor = await db.execute("INSERT INTO scan_runs (status) VALUES ('running')")
    scan_id = cursor.lastrowid
    await db.commit(); await db.close()
    return scan_id


async def complete_scan(scan_id: int, files_found: int, files_analyzed: int, duration: float):
    db = await get_db()
    await db.execute(
        "UPDATE scan_runs SET files_found=?, files_analyzed=?, duration_seconds=?, status='completed', completed_at=datetime('now') WHERE id=?",
        (files_found, files_analyzed, duration, scan_id))
    await db.commit(); await db.close()


async def get_scan_history():
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT 10")
    await db.close()
    return [dict(r) for r in rows]


async def get_unanalyzed_samples(limit: int = 50):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM samples WHERE analyzed=0 ORDER BY filename LIMIT ?", (limit,))
    await db.close()
    return [dict(r) for r in rows]


async def get_all_keys():
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT DISTINCT key FROM samples WHERE key != '' AND analyzed=1 ORDER BY key")
    await db.close()
    return [r[0] for r in rows]


async def get_all_directories():
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT DISTINCT directory FROM samples ORDER BY directory")
    await db.close()
    return [r[0] for r in rows]
