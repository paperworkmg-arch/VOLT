import sqlite3
import os

def migrate():
    db_path = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Make email nullable and add music-library columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            city TEXT,
            status TEXT DEFAULT 'SCRAPED',
            gate_code TEXT,
            sub_library TEXT,
            title TEXT,
            linkedin_url TEXT UNIQUE,
            source TEXT DEFAULT 'SCRAPED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT INTO leads_new (
            id, name, email, city, status, gate_code,
            sub_library, title, linkedin_url, source,
            created_at, last_updated
        )
        SELECT
            id, name, email, city, status, gate_code,
            NULL, NULL, NULL, 'SCRAPED',
            created_at, last_updated
        FROM leads
    """)

    cursor.execute("DROP TABLE leads")
    cursor.execute("ALTER TABLE leads_new RENAME TO leads")
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
