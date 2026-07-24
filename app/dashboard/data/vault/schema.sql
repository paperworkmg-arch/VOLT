-- Omi → Kimi Vault Schema
-- SQLite with FTS5 full-text search
-- Version: 1.0.0

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Omi sessions (device / conversation groupings)
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL UNIQUE,
    device_info TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw append-only transcript entries from Omi webhooks
CREATE TABLE IF NOT EXISTS raw_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    timestamp   REAL NOT NULL,              -- Unix epoch from Omi
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_ip   TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Daily aggregated transcript batches
CREATE TABLE IF NOT EXISTS transcript_batches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_date      DATE NOT NULL UNIQUE,
    content         TEXT NOT NULL,          -- concatenated daily transcript
    entry_count     INTEGER DEFAULT 0,
    char_count      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at    TIMESTAMP
);

-- Kimi extraction results
CREATE TABLE IF NOT EXISTS extractions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            INTEGER NOT NULL,
    model               TEXT DEFAULT 'moonshot-v1-128k',
    raw_response        TEXT,               -- raw Kimi response (for debugging)
    processing_time_ms  INTEGER,
    status              TEXT DEFAULT 'success' CHECK (status IN ('success', 'partial', 'failed')),
    error_message       TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES transcript_batches(id) ON DELETE CASCADE
);

-- ============================================================
-- ENTITY TABLES (extracted by Kimi)
-- ============================================================

-- Music IP: lyrics, melodies, concepts, hooks
CREATE TABLE IF NOT EXISTS music_ip (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id   INTEGER NOT NULL,
    title           TEXT,
    category        TEXT CHECK (category IN ('lyrics', 'melody', 'concept', 'hook', 'arrangement', 'other')),
    content         TEXT NOT NULL,          -- the actual lyrics / melody desc / concept
    mood            TEXT,
    tags            TEXT,                   -- JSON array of tags
    confidence      REAL CHECK (confidence BETWEEN 0.0 AND 1.0),
    source_context  TEXT,                   -- surrounding transcript context
    archived        INTEGER DEFAULT 0,      -- 0 = active, 1 = archived
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(id) ON DELETE CASCADE
);

-- CRM / Deal notes from meetings
CREATE TABLE IF NOT EXISTS crm_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id   INTEGER NOT NULL,
    deal_name       TEXT,
    contact_name    TEXT,
    company         TEXT,
    deal_stage      TEXT CHECK (deal_stage IN ('prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost', 'nurture')),
    notes           TEXT NOT NULL,
    action_items    TEXT,                   -- JSON array
    follow_up_date  DATE,
    deal_value      REAL,
    currency        TEXT DEFAULT 'USD',
    confidence      REAL CHECK (confidence BETWEEN 0.0 AND 1.0),
    source_context  TEXT,
    archived        INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(id) ON DELETE CASCADE
);

-- SOPs: procedures, workflows, logic dictates
CREATE TABLE IF NOT EXISTS sops (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id   INTEGER NOT NULL,
    title           TEXT NOT NULL,
    category        TEXT CHECK (category IN ('workflow', 'decision_tree', 'checklist', 'policy', 'automation', 'other')),
    content         TEXT NOT NULL,          -- the procedure / logic
    prerequisites   TEXT,                   -- JSON array
    related_tools   TEXT,                   -- JSON array
    confidence      REAL CHECK (confidence BETWEEN 0.0 AND 1.0),
    source_context  TEXT,
    archived        INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(id) ON DELETE CASCADE
);

-- Generic tag system
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    color       TEXT DEFAULT '#6366F1',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Polymorphic tagging (music_ip, crm_notes, sops)
CREATE TABLE IF NOT EXISTS taggings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id          INTEGER NOT NULL,
    taggable_type   TEXT NOT NULL CHECK (taggable_type IN ('music_ip', 'crm_notes', 'sops')),
    taggable_id     INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(tag_id, taggable_type, taggable_id)
);

-- ============================================================
-- FTS5 FULL-TEXT SEARCH VIRTUAL TABLES
-- ============================================================

CREATE VIRTUAL TABLE IF NOT EXISTS raw_entries_fts USING fts5(
    transcript,
    content='raw_entries',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS music_ip_fts USING fts5(
    title,
    content,
    mood,
    content='music_ip',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS crm_notes_fts USING fts5(
    deal_name,
    contact_name,
    company,
    notes,
    content='crm_notes',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS sops_fts USING fts5(
    title,
    content,
    content='sops',
    content_rowid='id'
);

-- ============================================================
-- TRIGGERS (sync FTS5 on insert/update/delete)
-- ============================================================

-- raw_entries FTS triggers
CREATE TRIGGER IF NOT EXISTS raw_entries_fts_insert AFTER INSERT ON raw_entries BEGIN
    INSERT INTO raw_entries_fts(rowid, transcript) VALUES (new.id, new.transcript);
END;

CREATE TRIGGER IF NOT EXISTS raw_entries_fts_delete AFTER DELETE ON raw_entries BEGIN
    INSERT INTO raw_entries_fts(raw_entries_fts, rowid, transcript) VALUES ('delete', old.id, old.transcript);
END;

-- music_ip FTS triggers
CREATE TRIGGER IF NOT EXISTS music_ip_fts_insert AFTER INSERT ON music_ip BEGIN
    INSERT INTO music_ip_fts(rowid, title, content, mood) VALUES (new.id, new.title, new.content, new.mood);
END;

CREATE TRIGGER IF NOT EXISTS music_ip_fts_delete AFTER DELETE ON music_ip BEGIN
    INSERT INTO music_ip_fts(music_ip_fts, rowid, title, content, mood) VALUES ('delete', old.id, old.title, old.content, old.mood);
END;

CREATE TRIGGER IF NOT EXISTS music_ip_fts_update AFTER UPDATE ON music_ip BEGIN
    INSERT INTO music_ip_fts(music_ip_fts, rowid, title, content, mood) VALUES ('delete', old.id, old.title, old.content, old.mood);
    INSERT INTO music_ip_fts(rowid, title, content, mood) VALUES (new.id, new.title, new.content, new.mood);
END;

-- crm_notes FTS triggers
CREATE TRIGGER IF NOT EXISTS crm_notes_fts_insert AFTER INSERT ON crm_notes BEGIN
    INSERT INTO crm_notes_fts(rowid, deal_name, contact_name, company, notes) VALUES (new.id, new.deal_name, new.contact_name, new.company, new.notes);
END;

CREATE TRIGGER IF NOT EXISTS crm_notes_fts_delete AFTER DELETE ON crm_notes BEGIN
    INSERT INTO crm_notes_fts(crm_notes_fts, rowid, deal_name, contact_name, company, notes) VALUES ('delete', old.id, old.deal_name, old.contact_name, old.company, old.notes);
END;

CREATE TRIGGER IF NOT EXISTS crm_notes_fts_update AFTER UPDATE ON crm_notes BEGIN
    INSERT INTO crm_notes_fts(crm_notes_fts, rowid, deal_name, contact_name, company, notes) VALUES ('delete', old.id, old.deal_name, old.contact_name, old.company, old.notes);
    INSERT INTO crm_notes_fts(rowid, deal_name, contact_name, company, notes) VALUES (new.id, new.deal_name, new.contact_name, new.company, new.notes);
END;

-- sops FTS triggers
CREATE TRIGGER IF NOT EXISTS sops_fts_insert AFTER INSERT ON sops BEGIN
    INSERT INTO sops_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS sops_fts_delete AFTER DELETE ON sops BEGIN
    INSERT INTO sops_fts(sops_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS sops_fts_update AFTER UPDATE ON sops BEGIN
    INSERT INTO sops_fts(sops_fts, rowid, title, content) VALUES ('delete', old.id, old.title, old.content);
    INSERT INTO sops_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
END;

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_raw_entries_session ON raw_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_raw_entries_timestamp ON raw_entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_entries_received ON raw_entries(received_at);

CREATE INDEX IF NOT EXISTS idx_batches_date ON transcript_batches(batch_date);
CREATE INDEX IF NOT EXISTS idx_batches_status ON transcript_batches(status);

CREATE INDEX IF NOT EXISTS idx_extractions_batch ON extractions(batch_id);
CREATE INDEX IF NOT EXISTS idx_extractions_created ON extractions(created_at);

CREATE INDEX IF NOT EXISTS idx_music_ip_category ON music_ip(category);
CREATE INDEX IF NOT EXISTS idx_music_ip_confidence ON music_ip(confidence);
CREATE INDEX IF NOT EXISTS idx_music_ip_archived ON music_ip(archived);

CREATE INDEX IF NOT EXISTS idx_crm_stage ON crm_notes(deal_stage);
CREATE INDEX IF NOT EXISTS idx_crm_contact ON crm_notes(contact_name);
CREATE INDEX IF NOT EXISTS idx_crm_company ON crm_notes(company);
CREATE INDEX IF NOT EXISTS idx_crm_followup ON crm_notes(follow_up_date);
CREATE INDEX IF NOT EXISTS idx_crm_archived ON crm_notes(archived);

CREATE INDEX IF NOT EXISTS idx_sops_category ON sops(category);
CREATE INDEX IF NOT EXISTS idx_sops_archived ON sops(archived);

CREATE INDEX IF NOT EXISTS idx_taggings_lookup ON taggings(taggable_type, taggable_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- Daily summary view
CREATE VIEW IF NOT EXISTS v_daily_summary AS
SELECT 
    b.batch_date,
    b.entry_count,
    b.char_count,
    b.status,
    COUNT(DISTINCT m.id) AS music_count,
    COUNT(DISTINCT c.id) AS crm_count,
    COUNT(DISTINCT s.id) AS sop_count
FROM transcript_batches b
LEFT JOIN extractions e ON e.batch_id = b.id
LEFT JOIN music_ip m ON m.extraction_id = e.id AND m.archived = 0
LEFT JOIN crm_notes c ON c.extraction_id = e.id AND c.archived = 0
LEFT JOIN sops s ON s.extraction_id = e.id AND s.archived = 0
GROUP BY b.batch_date;

-- Recent activity view
CREATE VIEW IF NOT EXISTS v_recent_activity AS
SELECT 
    'music_ip' AS entity_type,
    m.id AS entity_id,
    m.title,
    m.category,
    m.confidence,
    m.created_at,
    b.batch_date AS source_date
FROM music_ip m
JOIN extractions e ON e.id = m.extraction_id
JOIN transcript_batches b ON b.id = e.batch_id
WHERE m.archived = 0
UNION ALL
SELECT 
    'crm_notes' AS entity_type,
    c.id AS entity_id,
    c.deal_name AS title,
    c.deal_stage AS category,
    c.confidence,
    c.created_at,
    b.batch_date AS source_date
FROM crm_notes c
JOIN extractions e ON e.id = c.extraction_id
JOIN transcript_batches b ON b.id = e.batch_id
WHERE c.archived = 0
UNION ALL
SELECT 
    'sops' AS entity_type,
    s.id AS entity_id,
    s.title,
    s.category,
    s.confidence,
    s.created_at,
    b.batch_date AS source_date
FROM sops s
JOIN extractions e ON e.id = s.extraction_id
JOIN transcript_batches b ON b.id = e.batch_id
WHERE s.archived = 0
ORDER BY created_at DESC;

-- ============================================================
-- CATALOG TABLES (Volt Records track analytics)
-- ============================================================

CREATE TABLE IF NOT EXISTS catalog_tracks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    track_name          TEXT NOT NULL,
    bpm                 REAL NOT NULL,
    key                 TEXT NOT NULL,
    brightness          TEXT CHECK (brightness IN ('Bright/Aggressive', 'Warm/Dark')),
    energy_density      REAL,
    alpha               REAL,
    structural_velocity REAL,
    market_modularity   REAL,
    hpi                 REAL NOT NULL,
    verdict             TEXT,
    verdict_bucket      TEXT CHECK (verdict_bucket IN ('ACQUIRE', 'PITCH', 'PITCH+LICENSE', 'LICENSE', 'ANALYZE')),
    source_file         TEXT,               -- original analysis file path
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS catalog_tracks_fts USING fts5(
    track_name,
    verdict,
    content='catalog_tracks',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS catalog_tracks_fts_insert AFTER INSERT ON catalog_tracks BEGIN
    INSERT INTO catalog_tracks_fts(rowid, track_name, verdict) VALUES (new.id, new.track_name, new.verdict);
END;

CREATE TRIGGER IF NOT EXISTS catalog_tracks_fts_delete AFTER DELETE ON catalog_tracks BEGIN
    INSERT INTO catalog_tracks_fts(catalog_tracks_fts, rowid, track_name, verdict) VALUES ('delete', old.id, old.track_name, old.verdict);
END;

CREATE TRIGGER IF NOT EXISTS catalog_tracks_fts_update AFTER UPDATE ON catalog_tracks BEGIN
    INSERT INTO catalog_tracks_fts(catalog_tracks_fts, rowid, track_name, verdict) VALUES ('delete', old.id, old.track_name, old.verdict);
    INSERT INTO catalog_tracks_fts(rowid, track_name, verdict) VALUES (new.id, new.track_name, new.verdict);
END;

CREATE INDEX IF NOT EXISTS idx_catalog_hpi ON catalog_tracks(hpi);
CREATE INDEX IF NOT EXISTS idx_catalog_bpm ON catalog_tracks(bpm);
CREATE INDEX IF NOT EXISTS idx_catalog_key ON catalog_tracks(key);
CREATE INDEX IF NOT EXISTS idx_catalog_brightness ON catalog_tracks(brightness);
CREATE INDEX IF NOT EXISTS idx_catalog_bucket ON catalog_tracks(verdict_bucket);
CREATE INDEX IF NOT EXISTS idx_catalog_alpha ON catalog_tracks(alpha);

-- Catalog analytics view
CREATE VIEW IF NOT EXISTS v_catalog_summary AS
SELECT 
    COUNT(*) AS total_tracks,
    AVG(hpi) AS avg_hpi,
    AVG(bpm) AS avg_bpm,
    MIN(bpm) AS min_bpm,
    MAX(bpm) AS max_bpm,
    SUM(CASE WHEN hpi >= 8.5 THEN 1 ELSE 0 END) AS red_zone_count,
    SUM(CASE WHEN verdict_bucket = 'ACQUIRE' THEN 1 ELSE 0 END) AS acquire_count,
    SUM(CASE WHEN brightness = 'Bright/Aggressive' THEN 1 ELSE 0 END) AS bright_count,
    SUM(CASE WHEN brightness = 'Warm/Dark' THEN 1 ELSE 0 END) AS warm_count
FROM catalog_tracks;

-- Key distribution view
CREATE VIEW IF NOT EXISTS v_key_distribution AS
SELECT key, COUNT(*) AS count FROM catalog_tracks GROUP BY key ORDER BY count DESC;

-- Bucket distribution view
CREATE VIEW IF NOT EXISTS v_bucket_distribution AS
SELECT verdict_bucket AS bucket, COUNT(*) AS count FROM catalog_tracks GROUP BY verdict_bucket ORDER BY count DESC;
