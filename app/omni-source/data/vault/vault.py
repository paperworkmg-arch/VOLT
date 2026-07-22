"""
Omi → Kimi Vault DAO

Local-first SQLite storage for ambient transcript capture and
structured entity extraction. Supports FTS5 search, WAL mode,
and atomic batch processing.

Usage:
    from vault import Vault
    v = Vault("data/vault/vault.db")
    v.init_schema()
    v.log_raw_entry("sess_123", "meeting about deal with Acme", 1721234567.0)
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, date
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple


class VaultError(Exception):
    """Base exception for vault operations."""
    pass


class Vault:
    """SQLite-backed vault for Omi transcripts and Kimi extractions."""

    def __init__(self, db_path: str = "./data/vault/vault.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_path = Path(__file__).parent / "schema.sql"

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Initialize database from schema.sql. Idempotent."""
        if not self._schema_path.exists():
            raise VaultError(f"Schema file not found: {self._schema_path}")

        with self._connect() as conn:
            sql = self._schema_path.read_text(encoding="utf-8")
            conn.executescript(sql)

    def reset(self) -> None:
        """Drop all tables and reinitialize. DESTRUCTIVE."""
        with self._connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            for row in tables:
                name = row["name"]
                if not name.startswith("sqlite_"):
                    conn.execute(f"DROP TABLE IF EXISTS {name}")

            vtables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%VIRTUAL%fts5%'"
            ).fetchall()
            for row in vtables:
                conn.execute(f"DROP TABLE IF EXISTS {row['name']}")

        self.init_schema()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def upsert_session(self, session_id: str, device_info: Optional[str] = None) -> None:
        """Create or update an Omi session record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, device_info, last_seen_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_seen_at = CURRENT_TIMESTAMP,
                    device_info = COALESCE(EXCLUDED.device_info, device_info)
                """,
                (session_id, device_info),
            )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Raw entries (append-only)
    # ------------------------------------------------------------------

    def log_raw_entry(
        self,
        session_id: str,
        transcript: str,
        timestamp: float,
        source_ip: Optional[str] = None,
    ) -> int:
        """Append a raw transcript entry. Returns row id."""
        self.upsert_session(session_id)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO raw_entries (session_id, transcript, timestamp, source_ip)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, transcript, timestamp, source_ip),
            )
            return cur.lastrowid

    def get_raw_entries(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute(
                    """
                    SELECT * FROM raw_entries
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (session_id, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM raw_entries
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Transcript batches (daily aggregation)
    # ------------------------------------------------------------------

    def create_or_get_batch(self, batch_date: Optional[date] = None) -> int:
        """Get existing batch for date, or create new. Returns batch_id."""
        batch_date = batch_date or date.today()
        date_str = batch_date.isoformat()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM transcript_batches WHERE batch_date = ?",
                (date_str,),
            ).fetchone()
            if row:
                return row["id"]

            cur = conn.execute(
                """
                INSERT INTO transcript_batches (batch_date, content, status)
                VALUES (?, '', 'pending')
                """,
                (date_str,),
            )
            return cur.lastrowid

    def append_to_batch(
        self,
        transcript: str,
        batch_date: Optional[date] = None,
    ) -> int:
        """Append transcript to today's batch. Returns batch_id."""
        batch_id = self.create_or_get_batch(batch_date)
        char_count = len(transcript)

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE transcript_batches
                SET content = content || ?,
                    entry_count = entry_count + 1,
                    char_count = char_count + ?,
                    created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
                WHERE id = ?
                """,
                (f"\n{transcript}", char_count, batch_id),
            )
        return batch_id

    def get_batch(self, batch_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM transcript_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_batch_by_date(self, batch_date: date) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM transcript_batches WHERE batch_date = ?",
                (batch_date.isoformat(),),
            ).fetchone()
            return dict(row) if row else None

    def update_batch_status(
        self, batch_id: int, status: str, processed_at: bool = False
    ) -> None:
        with self._connect() as conn:
            if processed_at:
                conn.execute(
                    """
                    UPDATE transcript_batches
                    SET status = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, batch_id),
                )
            else:
                conn.execute(
                    "UPDATE transcript_batches SET status = ? WHERE id = ?",
                    (status, batch_id),
                )

    def list_batches(
        self,
        status: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM transcript_batches
                    WHERE status = ?
                    ORDER BY batch_date DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM transcript_batches
                    ORDER BY batch_date DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Extractions (Kimi output)
    # ------------------------------------------------------------------

    def create_extraction(
        self,
        batch_id: int,
        raw_response: str,
        model: str = "moonshot-v1-128k",
        processing_time_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> int:
        """Store a Kimi extraction result. Returns extraction_id."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO extractions
                (batch_id, model, raw_response, processing_time_ms, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (batch_id, model, raw_response, processing_time_ms, status, error_message),
            )
            return cur.lastrowid

    def get_extraction(self, extraction_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM extractions WHERE id = ?", (extraction_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Structured entity persistence
    # ------------------------------------------------------------------

    def save_kimi_extraction(
        self,
        batch_id: int,
        structured_data: Dict[str, Any],
        raw_response: str = "",
        model: str = "moonshot-v1-128k",
        processing_time_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Persist a complete Kimi structured extraction in one transaction.

        Expected structured_data shape:
        {
            "music_ip": [
                {"title": "...", "category": "lyrics", "content": "...", ...}
            ],
            "deals": [
                {"deal_name": "...", "notes": "...", ...}
            ],
            "sops": [
                {"title": "...", "category": "workflow", "content": "...", ...}
            ]
        }
        """
        with self._connect() as conn:
            # 1. Create extraction record
            cur = conn.execute(
                """
                INSERT INTO extractions
                (batch_id, model, raw_response, processing_time_ms, status)
                VALUES (?, ?, ?, ?, 'success')
                """,
                (batch_id, model, raw_response, processing_time_ms),
            )
            extraction_id = cur.lastrowid

            music_ids: List[int] = []
            crm_ids: List[int] = []
            sop_ids: List[int] = []

            # 2. Music IP
            for item in structured_data.get("music_ip", []):
                cur = conn.execute(
                    """
                    INSERT INTO music_ip
                    (extraction_id, title, category, content, mood, tags, confidence, source_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        extraction_id,
                        item.get("title"),
                        item.get("category", "other"),
                        item.get("content", ""),
                        item.get("mood"),
                        json.dumps(item.get("tags", [])) if isinstance(item.get("tags"), list) else item.get("tags"),
                        item.get("confidence", 0.8),
                        item.get("source_context"),
                    ),
                )
                music_ids.append(cur.lastrowid)

            # 3. CRM / Deals
            for item in structured_data.get("deals", []) or structured_data.get("crm_notes", []):
                cur = conn.execute(
                    """
                    INSERT INTO crm_notes
                    (extraction_id, deal_name, contact_name, company, deal_stage, notes,
                     action_items, follow_up_date, deal_value, currency, confidence, source_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        extraction_id,
                        item.get("deal_name"),
                        item.get("contact_name"),
                        item.get("company"),
                        item.get("deal_stage", "prospect"),
                        item.get("notes", ""),
                        json.dumps(item.get("action_items", [])) if isinstance(item.get("action_items"), list) else item.get("action_items"),
                        item.get("follow_up_date"),
                        item.get("deal_value"),
                        item.get("currency", "USD"),
                        item.get("confidence", 0.8),
                        item.get("source_context"),
                    ),
                )
                crm_ids.append(cur.lastrowid)

            # 4. SOPs
            for item in structured_data.get("sops", []):
                cur = conn.execute(
                    """
                    INSERT INTO sops
                    (extraction_id, title, category, content, prerequisites, related_tools, confidence, source_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        extraction_id,
                        item.get("title", "Untitled SOP"),
                        item.get("category", "other"),
                        item.get("content", ""),
                        json.dumps(item.get("prerequisites", [])) if isinstance(item.get("prerequisites"), list) else item.get("prerequisites"),
                        json.dumps(item.get("related_tools", [])) if isinstance(item.get("related_tools", []), list) else item.get("related_tools"),
                        item.get("confidence", 0.8),
                        item.get("source_context"),
                    ),
                )
                sop_ids.append(cur.lastrowid)

            # 5. Mark batch complete
            conn.execute(
                """
                UPDATE transcript_batches
                SET status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (batch_id,),
            )

        return {
            "extraction_id": extraction_id,
            "music_ip_ids": music_ids,
            "crm_ids": crm_ids,
            "sop_ids": sop_ids,
        }

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    def get_music_ip(
        self,
        category: Optional[str] = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if category:
                rows = conn.execute(
                    """
                    SELECT m.*, b.batch_date
                    FROM music_ip m
                    JOIN extractions e ON e.id = m.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE m.category = ? AND m.archived = ?
                    ORDER BY m.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (category, int(archived), limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.*, b.batch_date
                    FROM music_ip m
                    JOIN extractions e ON e.id = m.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE m.archived = ?
                    ORDER BY m.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (int(archived), limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_crm_notes(
        self,
        stage: Optional[str] = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if stage:
                rows = conn.execute(
                    """
                    SELECT c.*, b.batch_date
                    FROM crm_notes c
                    JOIN extractions e ON e.id = c.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE c.deal_stage = ? AND c.archived = ?
                    ORDER BY c.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (stage, int(archived), limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT c.*, b.batch_date
                    FROM crm_notes c
                    JOIN extractions e ON e.id = c.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE c.archived = ?
                    ORDER BY c.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (int(archived), limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_sops(
        self,
        category: Optional[str] = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if category:
                rows = conn.execute(
                    """
                    SELECT s.*, b.batch_date
                    FROM sops s
                    JOIN extractions e ON e.id = s.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE s.category = ? AND s.archived = ?
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (category, int(archived), limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT s.*, b.batch_date
                    FROM sops s
                    JOIN extractions e ON e.id = s.extraction_id
                    JOIN transcript_batches b ON b.id = e.batch_id
                    WHERE s.archived = ?
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (int(archived), limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    def archive_entity(self, entity_type: str, entity_id: int) -> None:
        """Soft-delete an entity by setting archived=1."""
        table = {"music_ip": "music_ip", "crm_notes": "crm_notes", "sops": "sops"}.get(entity_type)
        if not table:
            raise VaultError(f"Unknown entity type: {entity_type}")
        with self._connect() as conn:
            conn.execute(
                f"UPDATE {table} SET archived = 1 WHERE id = ?", (entity_id,)
            )

    # ------------------------------------------------------------------
    # FTS5 Search
    # ------------------------------------------------------------------

    def search_raw_entries(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search over raw transcript entries."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.*, rank
                FROM raw_entries r
                JOIN raw_entries_fts f ON r.id = f.rowid
                WHERE raw_entries_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_music_ip(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT m.*, rank
                FROM music_ip m
                JOIN music_ip_fts f ON m.id = f.rowid
                WHERE music_ip_fts MATCH ? AND m.archived = 0
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_crm(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, rank
                FROM crm_notes c
                JOIN crm_notes_fts f ON c.id = f.rowid
                WHERE crm_notes_fts MATCH ? AND c.archived = 0
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_sops(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*, rank
                FROM sops s
                JOIN sops_fts f ON s.id = f.rowid
                WHERE sops_fts MATCH ? AND s.archived = 0
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_all(self, query: str, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all entity types."""
        return {
            "raw_entries": self.search_raw_entries(query, limit),
            "music_ip": self.search_music_ip(query, limit),
            "crm_notes": self.search_crm(query, limit),
            "sops": self.search_sops(query, limit),
        }

    # ------------------------------------------------------------------
    # Views / Analytics
    # ------------------------------------------------------------------

    def get_daily_summary(self, batch_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            if batch_date:
                row = conn.execute(
                    "SELECT * FROM v_daily_summary WHERE batch_date = ?",
                    (batch_date.isoformat(),),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM v_daily_summary ORDER BY batch_date DESC LIMIT 1"
                ).fetchone()
            return dict(row) if row else None

    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM v_recent_activity LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def create_tag(self, name: str, color: str = "#6366F1") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO tags (name, color) VALUES (?, ?)",
                (name, color),
            )
            if cur.lastrowid:
                return cur.lastrowid
            row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
            return row["id"]

    def tag_entity(self, tag_id: int, entity_type: str, entity_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO taggings (tag_id, taggable_type, taggable_id)
                VALUES (?, ?, ?)
                """,
                (tag_id, entity_type, entity_id),
            )

    def get_entity_tags(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT t.* FROM tags t
                JOIN taggings tg ON tg.tag_id = t.id
                WHERE tg.taggable_type = ? AND tg.taggable_id = ?
                """,
                (entity_type, entity_id),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total_entries = conn.execute(
                "SELECT COUNT(*) AS c FROM raw_entries"
            ).fetchone()["c"]
            total_batches = conn.execute(
                "SELECT COUNT(*) AS c FROM transcript_batches"
            ).fetchone()["c"]
            total_music = conn.execute(
                "SELECT COUNT(*) AS c FROM music_ip WHERE archived = 0"
            ).fetchone()["c"]
            total_crm = conn.execute(
                "SELECT COUNT(*) AS c FROM crm_notes WHERE archived = 0"
            ).fetchone()["c"]
            total_sops = conn.execute(
                "SELECT COUNT(*) AS c FROM sops WHERE archived = 0"
            ).fetchone()["c"]
            pending_batches = conn.execute(
                "SELECT COUNT(*) AS c FROM transcript_batches WHERE status = 'pending'"
            ).fetchone()["c"]

        return {
            "total_raw_entries": total_entries,
            "total_batches": total_batches,
            "pending_batches": pending_batches,
            "total_music_ip": total_music,
            "total_crm_notes": total_crm,
            "total_sops": total_sops,
        }

    # ------------------------------------------------------------------
    # Catalog Tracks (Volt Records)
    # ------------------------------------------------------------------

    def import_catalog_track(
        self,
        track_name: str,
        bpm: float,
        key: str,
        brightness: str,
        energy_density: float,
        alpha: float,
        structural_velocity: float,
        market_modularity: float,
        hpi: float,
        verdict: str,
        source_file: Optional[str] = None,
    ) -> int:
        """Import a single catalog track. Returns row id."""
        # Normalize bucket
        v = verdict.lower()
        if "acquisition" in v:
            bucket = "ACQUIRE"
        elif "playlist" in v and ("licensing" in v or "monetization" in v):
            bucket = "PITCH+LICENSE"
        elif "playlist" in v:
            bucket = "PITCH"
        elif "licensing" in v or "monetization" in v:
            bucket = "LICENSE"
        else:
            bucket = "ANALYZE"

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO catalog_tracks
                (track_name, bpm, key, brightness, energy_density, alpha,
                 structural_velocity, market_modularity, hpi, verdict, verdict_bucket, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (track_name, bpm, key, brightness, energy_density, alpha,
                 structural_velocity, market_modularity, hpi, verdict, bucket, source_file),
            )
            return cur.lastrowid or 0

    def import_catalog_tracks(self, tracks: List[Dict[str, Any]], source_file: Optional[str] = None) -> int:
        """Bulk import catalog tracks. Returns count imported."""
        count = 0
        for t in tracks:
            row_id = self.import_catalog_track(
                track_name=t.get("track", ""),
                bpm=t.get("bpm", 0.0),
                key=t.get("key", ""),
                brightness=t.get("brightness", "Bright/Aggressive"),
                energy_density=t.get("energy_density", 0.0),
                alpha=t.get("alpha", 0.0),
                structural_velocity=t.get("structural_velocity", 0.0),
                market_modularity=t.get("market_modularity", 0.0),
                hpi=t.get("hpi", 0.0),
                verdict=t.get("verdict", ""),
                source_file=source_file,
            )
            if row_id:
                count += 1
        return count

    def get_catalog_tracks(
        self,
        bucket: Optional[str] = None,
        key: Optional[str] = None,
        brightness: Optional[str] = None,
        hpi_min: float = 0.0,
        hpi_max: float = 10.0,
        bpm_min: float = 0.0,
        bpm_max: float = 999.0,
        search: Optional[str] = None,
        sort_by: str = "hpi",
        sort_desc: bool = True,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query catalog tracks with filters."""
        with self._connect() as conn:
            conditions = ["hpi >= ?", "hpi <= ?", "bpm >= ?", "bpm <= ?"]
            params: List[Any] = [hpi_min, hpi_max, bpm_min, bpm_max]

            if bucket:
                conditions.append("verdict_bucket = ?")
                params.append(bucket)
            if key:
                conditions.append("key = ?")
                params.append(key)
            if brightness:
                conditions.append("brightness = ?")
                params.append(brightness)

            where_clause = " AND ".join(conditions)

            if search:
                # Use FTS5 for text search, then join
                rows = conn.execute(
                    f"""
                    SELECT ct.* FROM catalog_tracks ct
                    JOIN catalog_tracks_fts f ON ct.id = f.rowid
                    WHERE catalog_tracks_fts MATCH ? AND {where_clause}
                    ORDER BY ct.{sort_by} DESC
                    LIMIT ? OFFSET ?
                    """,
                    (search, *params, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"""
                    SELECT * FROM catalog_tracks
                    WHERE {where_clause}
                    ORDER BY {sort_by} DESC
                    LIMIT ? OFFSET ?
                    """,
                    (*params, limit, offset),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_catalog_summary(self) -> Dict[str, Any]:
        """Get aggregate stats for the catalog."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM v_catalog_summary").fetchone()
            if not row:
                return {}
            return dict(row)

    def get_catalog_by_key(self) -> List[Dict[str, Any]]:
        """Key distribution."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM v_key_distribution").fetchall()
            return [dict(r) for r in rows]

    def get_catalog_by_bucket(self) -> List[Dict[str, Any]]:
        """Bucket/strategy distribution."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM v_bucket_distribution").fetchall()
            return [dict(r) for r in rows]

    def search_catalog(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search over catalog."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ct.*, rank FROM catalog_tracks ct
                JOIN catalog_tracks_fts f ON ct.id = f.rowid
                WHERE catalog_tracks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_top_prospects(self, n: int = 6) -> List[Dict[str, Any]]:
        """Top N tracks by HPI, then market_modularity, then alpha."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM catalog_tracks
                ORDER BY hpi DESC, market_modularity DESC, alpha DESC, track_name ASC
                LIMIT ?
                """,
                (n,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM catalog_tracks WHERE id = ?", (track_id,)
            ).fetchone()
            return dict(row) if row else None

    def clear_catalog(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM catalog_tracks")


# ----------------------------------------------------------------------
# CLI / Test helpers
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Omi Vault CLI")
    parser.add_argument("--init", action="store_true", help="Initialize schema")
    parser.add_argument("--reset", action="store_true", help="Reset database")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    parser.add_argument("--db", default="./data/vault/vault.db", help="DB path")
    args = parser.parse_args()

    vault = Vault(args.db)

    if args.reset:
        vault.reset()
        print("Vault reset and reinitialized.")
    elif args.init:
        vault.init_schema()
        print("Vault schema initialized.")
    elif args.stats:
        print(json.dumps(vault.get_stats(), indent=2))
    else:
        vault.init_schema()
        print("Vault ready.")
        print(json.dumps(vault.get_stats(), indent=2))
