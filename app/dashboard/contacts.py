"""
Contacts / CRM module for Omni-Studio.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "contacts.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_contacts_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            company TEXT,
            role TEXT,
            source TEXT,
            status TEXT DEFAULT 'lead',
            tags TEXT DEFAULT '[]',
            notes TEXT,
            last_contact TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
        CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company);
        CREATE INDEX IF NOT EXISTS idx_contacts_source ON contacts(source);
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def list_contacts(status: str = "", search: str = "", limit: int = 100, offset: int = 0) -> dict:
    init_contacts_db()
    conn = _get_conn()
    conditions = []
    params = []
    if status:
        conditions.append("status=?")
        params.append(status)
    if search:
        like = f"%{search}%"
        conditions.append("(name LIKE ? OR email LIKE ? OR company LIKE ? OR notes LIKE ?)")
        params.extend([like, like, like, like])
    where = " AND ".join(conditions) if conditions else "1=1"

    count_row = conn.execute(f"SELECT COUNT(*) FROM contacts WHERE {where}", params).fetchone()
    total = count_row[0]
    rows = conn.execute(
        f"SELECT * FROM contacts WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    conn.close()
    return {"contacts": [_row_to_dict(r) for r in rows], "total": total}


def get_contact(contact_id: int) -> dict | None:
    init_contacts_db()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def create_contact(data: dict) -> int:
    init_contacts_db()
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO contacts
           (name, email, phone, company, role, source, status, tags, notes, last_contact)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("name"), data.get("email"), data.get("phone"),
            data.get("company"), data.get("role"), data.get("source"),
            data.get("status", "lead"), data.get("tags", "[]"),
            data.get("notes"), data.get("last_contact")
        )
    )
    conn.commit()
    contact_id = cursor.lastrowid
    conn.close()
    return contact_id


def update_contact(contact_id: int, data: dict):
    init_contacts_db()
    conn = _get_conn()
    allowed = {"name", "email", "phone", "company", "role", "source", "status", "tags", "notes", "last_contact"}
    fields = []
    values = []
    for k, v in data.items():
        if k in allowed:
            fields.append(f"{k}=?")
            values.append(v)
    if not fields:
        conn.close()
        return
    values.append(contact_id)
    conn.execute(
        f"UPDATE contacts SET {', '.join(fields)}, updated_at=datetime('now') WHERE id=?",
        values
    )
    conn.commit()
    conn.close()


def delete_contact(contact_id: int):
    init_contacts_db()
    conn = _get_conn()
    conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()


def import_csv(csv_path: Path) -> int:
    """Import contacts from a CSV file (name,email,company,role,status)."""
    import csv
    init_contacts_db()
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            create_contact({
                "name": row.get("name", ""),
                "email": row.get("email", ""),
                "company": row.get("company", ""),
                "role": row.get("role", ""),
                "status": row.get("status", "lead"),
                "source": row.get("source", "csv_import"),
            })
            count += 1
    return count
