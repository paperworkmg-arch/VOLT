#!/usr/bin/env python3
"""
Music Library Schema Migration — creates/updates studio_crm.db with all
tables needed by the lead pipeline, income watchdog, and music library aggregator.

Usage:
    python3 migrate_music_library_schema.py migrate     # create/update tables
    python3 migrate_music_library_schema.py status      # show table info
    python3 migrate_music_library_schema.py seed        # seed sample data
"""
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "studio_crm.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # === leads table (music_library_aggregator + audit_missed_funds) ===
    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            city TEXT,
            phone TEXT,
            company TEXT,
            role TEXT,
            status TEXT DEFAULT 'SCRAPED',
            gate_code TEXT,
            sub_library TEXT,
            title TEXT,
            linkedin_url TEXT,
            source TEXT DEFAULT 'SCRAPED',
            notes TEXT,
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === pitches table (press_pitch_generator) ===
    c.execute("""
        CREATE TABLE IF NOT EXISTS pitches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            outlet TEXT,
            media_type TEXT,
            contact_email TEXT,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'DRAFT',
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    # === payments table (income_watchdog) ===
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            artist_name TEXT,
            amount REAL,
            platform TEXT,
            matched_from TEXT,
            gate_code TEXT,
            status TEXT DEFAULT 'CONFIRMED',
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    # === sessions table (studio bookings) ===
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            artist_name TEXT,
            session_date TEXT,
            duration_hours REAL DEFAULT 1.0,
            gate_code TEXT,
            status TEXT DEFAULT 'SCHEDULED',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
    """)

    # === media_contacts table (generate_national_contacts) ===
    c.execute("""
        CREATE TABLE IF NOT EXISTS media_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outlet TEXT,
            media_type TEXT,
            contact_email TEXT,
            notes TEXT,
            tier TEXT DEFAULT 'NATIONAL',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_leads_linkedin ON leads(linkedin_url)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pitches_status ON pitches(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")

    conn.commit()
    conn.close()
    print(f"✅ Migration complete. Database: {DB_PATH}")


def status():
    if not DB_PATH.exists():
        print("⚠️  Database does not exist yet. Run: python3 migrate_music_library_schema.py migrate")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print(f"\n📊 Database: {DB_PATH}")
    print(f"   Tables: {len(tables)}\n")

    for (table,) in tables:
        count = c.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        cols = c.execute(f"PRAGMA table_info([{table}])").fetchall()
        print(f"   {table}: {count} rows, {len(cols)} columns")
        for col in cols:
            print(f"     - {col[1]} ({col[2]})")

    conn.close()


def seed():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Seed sample leads
    sample_leads = [
        ("Sarah Chen", "sarah@apmmusic.com", "Los Angeles", "APM Music", "MUSIC_LIBRARY_TARGET", "KPM", "https://linkedin.com/in/sarah-chen-kpm"),
        ("Marcus Williams", "marcus@upm.com", "Nashville", "Universal Production Music", "MUSIC_LIBRARY_TARGET", "FirstCom", "https://linkedin.com/in/marcus-williams"),
        ("DJ Khaled", "khaled@wethebest.com", "Miami", "We The Best Music", "SCRAPED", None, None),
        ("Jennifer Adams", "jennifer@sonoton.com", "London", "Sonoton Music", "MUSIC_LIBRARY_TARGET", "Sonoton", "https://linkedin.com/in/jennifer-adams-sonoton"),
    ]

    inserted = 0
    for name, email, city, company, status, sub_library, linkedin in sample_leads:
        try:
            c.execute(
                "INSERT INTO leads (name, email, city, company, status, sub_library, linkedin_url, source) VALUES (?,?,?,?,?,?,?,?)",
                (name, email, city, company, status, sub_library, linkedin, status)
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    # Seed sample media contacts
    sample_contacts = [
        ("Billboard", "Music/Business", "charts@billboard.com", "Industry gold standard"),
        ("Rolling Stone", "Music/Global", "music@rollingstone.com", "Global prestige"),
        ("TechCrunch", "Tech/Business", "tips@techcrunch.com", "Premier tech portal"),
        ("Complex", "Music/Culture", "music@complex.com", "National urban vanguard"),
        ("XXL Mag", "Music", "xxl@xxlmag.com", "Hip-hop authority"),
    ]

    for outlet, mtype, email, notes in sample_contacts:
        c.execute(
            "INSERT INTO media_contacts (outlet, media_type, contact_email, notes) VALUES (?,?,?,?)",
            (outlet, mtype, email, notes)
        )

    conn.commit()
    conn.close()
    print(f"✅ Seeded {inserted} leads and {len(sample_contacts)} media contacts")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    {"migrate": migrate, "status": status, "seed": seed}.get(cmd, lambda: print(f"Unknown command: {cmd}. Use: migrate, status, seed"))()
