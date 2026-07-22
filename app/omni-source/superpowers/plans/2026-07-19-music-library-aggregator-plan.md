# Music Library Aggregator Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, integrate, and verify a `music_library_aggregator.py` module inside Omni Studio that discovers A&R contacts at APM/UPM sub-libraries and persists them into the existing `studio_crm.db`.

**Architecture:** A single async Python script runs in the `master_orchestrator.py` cycle. It uses Serper.dev to execute LinkedIn dorks, Gemini 1.5 Pro with structured output to extract contacts, and SQLite upserts into the shared `leads` table. The `leads` schema is extended to support nullable emails and store `sub_library`, `title`, `linkedin_url`, and `source`.

**Tech Stack:** Python 3.14 (existing `.venv`), Playwright, `httpx`, `google-genai`, `pydantic`, SQLite.

## Global Constraints

- All code runs inside `/Users/mtb/Omni-Studio/` and uses its existing `.venv` interpreter at `~/Omni-Studio/.venv/bin/python3`.
- API keys are read from environment variables only (`SERPER_API_KEY`, `GEMINI_API_KEY`).
- Log format must match existing scripts: `%(asctime)s | %(levelname)s | %(message)s`.
- Single-line log messages so `master_orchestrator.py` forwards them cleanly.
- Database path is `~/Omni-Studio/studio_crm.db`.
- No email extraction from LinkedIn; only public name, title, and profile URL.
- No outreach generation in this iteration (collect contacts only).
- Dry-run mode uses `MLA_DRY_RUN=1` env var.

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `~/Omni-Studio/music_library_aggregator.py` | Create | Main module: library roster, Serper dorking, Gemini extraction, DB persistence. |
| `~/Omni-Studio/migrate_music_library_schema.py` | Create | One-time DB schema migration script. |
| `~/Omni-Studio/view_leads.py` | Modify | Show `source` breakdown and music-library columns. |
| `~/Omni-Studio/master_orchestrator.py` | Modify | Register module in `SCRIPTS` dict. |
| `~/Omni-Studio/tests/test_music_library_aggregator.py` | Create | Unit + integration tests with mocked APIs and temp DB. |
| `~/Omni-Studio/tests/fixtures/serper_sample.json` | Create | Sample Serper response for dry-run/tests. |
| `~/Omni-Studio/.venv` | Modify | Install `httpx` into venv. |

---

## Task 1: Install `httpx` into the Omni Studio venv

**Files:**
- Modify: `~/Omni-Studio/.venv/...` (dependency state)

**Interfaces:**
- Consumes: existing `.venv`.
- Produces: `httpx` importable by the new module.

- [ ] **Step 1: Install httpx**

```bash
/Users/mtb/Omni-Studio/.venv/bin/pip install httpx
```

- [ ] **Step 2: Verify installation**

Run:
```bash
/Users/mtb/Omni-Studio/.venv/bin/python3 -c "import httpx; print(httpx.__version__)"
```

Expected: version string printed, no import error.

- [ ] **Step 3: Commit**

Not required (venv is typically gitignored). Document the dependency in the module docstring instead.

---

## Task 2: Create the DB schema migration script

**Files:**
- Create: `~/Omni-Studio/migrate_music_library_schema.py`

**Interfaces:**
- Consumes: existing `studio_crm.db` schema.
- Produces: `leads` table with nullable `email` plus new columns `sub_library`, `title`, `linkedin_url`, `source`.

- [ ] **Step 1: Write the migration script**

```python
import sqlite3
import os

def migrate():
    db_path = os.path.expanduser('~/Omni-Studio/studio_crm.db')
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
```

- [ ] **Step 2: Back up the existing database before running**

Run:
```bash
cp /Users/mtb/Omni-Studio/studio_crm.db /Users/mtb/Omni-Studio/studio_crm.db.bak.$(date +%s)
```

- [ ] **Step 3: Run the migration**

Run:
```bash
/Users/mtb/Omni-Studio/.venv/bin/python3 /Users/mtb/Omni-Studio/migrate_music_library_schema.py
```

Expected output: `Migration complete.`

- [ ] **Step 4: Verify schema**

Run:
```bash
sqlite3 /Users/mtb/Omni-Studio/studio_crm.db ".schema leads"
```

Expected: `email` has no `NOT NULL`, and columns `sub_library`, `title`, `linkedin_url`, `source` exist.

- [ ] **Step 5: Commit**

```bash
git add /Users/mtb/Omni-Studio/migrate_music_library_schema.py
git commit -m "feat: add schema migration for music library targets"
```

---

## Task 3: Create the core aggregator module

**Files:**
- Create: `~/Omni-Studio/music_library_aggregator.py`

**Interfaces:**
- Consumes: `SERPER_API_KEY`, `GEMINI_API_KEY`, `MLA_DRY_RUN` env vars.
- Produces: inserts rows into `studio_crm.db` with `source='MUSIC_LIBRARY_TARGET'`.

- [ ] **Step 1: Write the module**

```python
"""
music_library_aggregator.py — Omni Studio module for APM/UPM sub-library A&R discovery.

Dependencies (install into .venv):
    pip install httpx google-genai pydantic

Environment:
    SERPER_API_KEY  - required for LinkedIn dorking
    GEMINI_API_KEY  - required for contact extraction
    MLA_DRY_RUN=1   - optional; uses fixtures instead of live APIs
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from typing import List

import httpx
from google import genai
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('Music-Library-Aggregator')

SERPER_API_KEY = os.getenv('SERPER_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DRY_RUN = os.getenv('MLA_DRY_RUN', '0') == '1'

DB_PATH = os.path.expanduser('~/Omni-Studio/studio_crm.db')

CORE_LIBRARIES = [
    # APM sub-labels
    "KPM", "Bruton", "Kosinus", "Sonoton", "Cezame", "Liquid Cinema",
    # UPM sub-labels
    "FirstCom", "Chappell", "Atmosphere", "Elias Music", "Chronic Trax",
    "Capitol Studio Masters",
]

class Target(BaseModel):
    name: str
    title: str
    sub_library: str
    linkedin_url: str

class TargetList(BaseModel):
    targets: List[Target]

def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
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
    conn.commit()
    conn.close()

def save_targets(targets: List[dict]) -> int:
    inserted = 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for t in targets:
        try:
            cursor.execute("""
                INSERT INTO leads (name, title, sub_library, linkedin_url, status, source)
                VALUES (?, ?, ?, ?, 'MUSIC_LIBRARY_TARGET', 'MUSIC_LIBRARY_TARGET')
            """, (t['name'], t['title'], t['sub_library'], t['linkedin_url']))
            inserted += 1
            logger.info(f"New target: {t['name']} | {t['title']} | {t['sub_library']}")
        except sqlite3.IntegrityError:
            logger.debug(f"Duplicate linkedin_url, skipping: {t['linkedin_url']}")
        except Exception as e:
            logger.error(f"DB insert error: {e}")
    conn.commit()
    conn.close()
    return inserted

def build_dork(library_name: str) -> str:
    return (
        f'site:linkedin.com/in/ '
        f'("A&R" OR "Creative Director" OR "Catalog Manager") '
        f'"{library_name}"'
    )

async def dork_linkedin(client: httpx.AsyncClient, library_name: str) -> List[dict]:
    if DRY_RUN:
        fixture_path = os.path.expanduser('~/Omni-Studio/tests/fixtures/serper_sample.json')
        with open(fixture_path) as f:
            return json.load(f)

    query = build_dork(library_name)
    payload = {"q": query, "num": 10}
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    try:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])
    except httpx.HTTPStatusError as e:
        logger.error(f"Serper HTTP error for {library_name}: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Serper request failed for {library_name}: {e}")
        return []

def extract_targets(raw_results: List[dict], library_name: str) -> List[dict]:
    if DRY_RUN:
        return [
            {
                "name": "Jane Doe",
                "title": "A&R Manager",
                "sub_library": library_name,
                "linkedin_url": f"https://linkedin.com/in/jane-doe-{library_name.lower()}"
            }
        ]

    genai_client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""You are an intelligence extractor. Review the raw Google Search JSON output for '{library_name}'.
Identify individuals who work in A&R, Creative Direction, or Catalog Management for this sub-library.
Filter out false positives, especially people who work for the parent companies APM Music or Universal Production Music rather than the boutique sub-library '{library_name}'.

Raw Data:
{json.dumps(raw_results)}
"""

    try:
        response = genai_client.models.generate_content(
            model='gemini-1.5-pro',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': TargetList,
                'temperature': 0.1,
            },
        )
        data = json.loads(response.text)
        return data.get("targets", [])
    except Exception as e:
        logger.error(f"Gemini extraction failed for {library_name}: {e}")
        return []

async def main():
    if not DRY_RUN and (not SERPER_API_KEY or not GEMINI_API_KEY):
        logger.error("Missing SERPER_API_KEY or GEMINI_API_KEY. Exiting.")
        sys.exit(1)

    ensure_db()
    logger.info(f"Scanning {len(CORE_LIBRARIES)} sub-libraries...")

    total_inserted = 0
    async with httpx.AsyncClient() as client:
        for lib in CORE_LIBRARIES:
            logger.info(f"Scanning {lib}...")
            try:
                raw = await dork_linkedin(client, lib)
                if not raw:
                    logger.info(f"No Serper results for {lib}")
                    continue
                targets = extract_targets(raw, lib)
                inserted = save_targets(targets)
                total_inserted += inserted
                logger.info(f"{lib}: inserted {inserted} new targets")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unhandled error scanning {lib}: {e}")

    logger.info(f"Music Library Aggregator complete. Total new targets inserted: {total_inserted}")

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run a syntax check**

Run:
```bash
/Users/mtb/Omni-Studio/.venv/bin/python3 -m py_compile /Users/mtb/Omni-Studio/music_library_aggregator.py
```

Expected: no output (success).

- [ ] **Step 3: Commit**

```bash
git add /Users/mtb/Omni-Studio/music_library_aggregator.py
git commit -m "feat: add music library aggregator module"
```

---

## Task 4: Add test fixtures and unit/integration tests

**Files:**
- Create: `~/Omni-Studio/tests/fixtures/serper_sample.json`
- Create: `~/Omni-Studio/tests/test_music_library_aggregator.py`

**Interfaces:**
- Consumes: `music_library_aggregator.py` functions, fixture JSON.
- Produces: passing pytest suite.

- [ ] **Step 1: Create fixture file**

```json
[
  {
    "title": "Jane Doe - A&R Manager - KPM Music | LinkedIn",
    "link": "https://www.linkedin.com/in/jane-doe-kpm",
    "snippet": "A&R Manager at KPM Music. Experienced in production music, catalog development, and artist relations."
  },
  {
    "title": "John Smith - Creative Director - Universal Production Music | LinkedIn",
    "link": "https://www.linkedin.com/in/john-smith-upm",
    "snippet": "Creative Director at Universal Production Music, overseeing film and trailer music."
  }
]
```

- [ ] **Step 2: Write tests**

```python
import os
import sqlite3
import sys
import pytest

sys.path.insert(0, os.path.expanduser('~/Omni-Studio'))

import music_library_aggregator as mla

def test_build_dork():
    dork = mla.build_dork("KPM")
    assert 'site:linkedin.com/in/' in dork
    assert '"KPM"' in dork
    assert '"A&R"' in dork

def test_ensure_db(tmp_path):
    original = mla.DB_PATH
    mla.DB_PATH = str(tmp_path / "test.db")
    try:
        mla.ensure_db()
        conn = sqlite3.connect(mla.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        assert cursor.fetchone()
        conn.close()
    finally:
        mla.DB_PATH = original

def test_save_targets(tmp_path):
    original = mla.DB_PATH
    mla.DB_PATH = str(tmp_path / "test.db")
    try:
        mla.ensure_db()
        targets = [
            {"name": "Jane Doe", "title": "A&R", "sub_library": "KPM", "linkedin_url": "https://linkedin.com/in/jane"},
            {"name": "John Smith", "title": "Creative Director", "sub_library": "FirstCom", "linkedin_url": "https://linkedin.com/in/john"},
        ]
        inserted = mla.save_targets(targets)
        assert inserted == 2

        # Duplicate run should insert 0
        inserted = mla.save_targets(targets)
        assert inserted == 0
    finally:
        mla.DB_PATH = original
```

- [ ] **Step 3: Install pytest if absent and run tests**

Run:
```bash
/Users/mtb/Omni-Studio/.venv/bin/pip install pytest
/Users/mtb/Omni-Studio/.venv/bin/python3 -m pytest /Users/mtb/Omni-Studio/tests/test_music_library_aggregator.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add /Users/mtb/Omni-Studio/tests
git commit -m "test: add music library aggregator tests and fixtures"
```

---

## Task 5: Update `view_leads.py` to surface music-library targets

**Files:**
- Modify: `~/Omni-Studio/view_leads.py`

**Interfaces:**
- Consumes: updated `leads` schema.
- Produces: console output now shows source breakdown and music-library columns.

- [ ] **Step 1: Add source-aware breakdown**

In the breakdown loop, add handling for `MUSIC_LIBRARY_TARGET`:

```python
elif status == 'MUSIC_LIBRARY_TARGET':
    source = "🎵 Music Library Aggregator"
```

- [ ] **Step 2: Add a separate music-library target table**

After the existing leads display, query and print music-library targets:

```python
cursor.execute("""
    SELECT name, title, sub_library, linkedin_url
    FROM leads
    WHERE source = 'MUSIC_LIBRARY_TARGET'
    ORDER BY sub_library, name
    LIMIT 100
""")
music_targets = cursor.fetchall()
if music_targets:
    print("\n 🎵 MUSIC LIBRARY TARGETS:")
    print(f"{'NAME':<20} | {'TITLE':<25} | {'SUB-LIBRARY':<15} | LINKEDIN")
    print("-" * 100)
    for row in music_targets:
        print(f"{str(row[0]):<20} | {str(row[1]):<25} | {str(row[2]):<15} | {row[3]}")
```

- [ ] **Step 3: Run view_leads.py to verify no errors**

Run:
```bash
/Users/mtb/Omni-Studio/.venv/bin/python3 /Users/mtb/Omni-Studio/view_leads.py
```

Expected: breakdown includes Music Library Aggregator source if targets exist; no traceback.

- [ ] **Step 4: Commit**

```bash
git add /Users/mtb/Omni-Studio/view_leads.py
git commit -m "feat: display music library targets in view_leads"
```

---

## Task 6: Register the module in `master_orchestrator.py`

**Files:**
- Modify: `~/Omni-Studio/master_orchestrator.py`

**Interfaces:**
- Consumes: `music_library_aggregator.py`.
- Produces: orchestrator runs the module each cycle.

- [ ] **Step 1: Add to SCRIPTS dict**

Update the `SCRIPTS` dictionary:

```python
SCRIPTS = {
    'Scraper': 'scraper.py',
    'Outbound Pitcher': 'send_ar_pitches.py',
    'Inbound AI Agent': 'inbound_agent.py',
    'Income Watchdog': 'income_watchdog.py',
    'Music Library Aggregator': 'music_library_aggregator.py',
}
```

- [ ] **Step 2: Verify orchestrator still starts**

Run a quick start/stop:

```bash
timeout 5 /Users/mtb/Omni-Studio/.venv/bin/python3 /Users/mtb/Omni-Studio/master_orchestrator.py || true
```

Expected: logs show master cycle beginning, possibly Music Library Aggregator runs once if keys are set; no syntax errors.

- [ ] **Step 3: Commit**

```bash
git add /Users/mtb/Omni-Studio/master_orchestrator.py
git commit -m "feat: register music library aggregator in orchestrator"
```

---

## Task 7: Dry-run verification without API keys

**Files:**
- Use: `~/Omni-Studio/music_library_aggregator.py`, fixture file.

**Interfaces:**
- Consumes: `MLA_DRY_RUN=1`.
- Produces: test rows inserted into DB.

- [ ] **Step 1: Run the module in dry-run mode**

Run:
```bash
MLA_DRY_RUN=1 /Users/mtb/Omni-Studio/.venv/bin/python3 /Users/mtb/Omni-Studio/music_library_aggregator.py
```

Expected: logs show scanning each library and inserting one fixture target per library.

- [ ] **Step 2: Verify DB rows**

Run:
```bash
sqlite3 /Users/mtb/Omni-Studio/studio_crm.db "SELECT COUNT(*) FROM leads WHERE source='MUSIC_LIBRARY_TARGET';"
```

Expected: count equals `len(CORE_LIBRARIES)` (12).

- [ ] **Step 3: Clean up dry-run rows**

Run:
```bash
sqlite3 /Users/mtb/Omni-Studio/studio_crm.db "DELETE FROM leads WHERE source='MUSIC_LIBRARY_TARGET';"
```

- [ ] **Step 4: Commit**

No code change; no commit needed. Record verification result in PR notes.

---

## Task 8: Production smoke test (requires API keys)

**Files:**
- Use: `~/Omni-Studio/music_library_aggregator.py`.

**Interfaces:**
- Consumes: `SERPER_API_KEY`, `GEMINI_API_KEY` env vars.
- Produces: real targets inserted into DB.

- [ ] **Step 1: Run with live keys on a subset**

Temporarily edit `CORE_LIBRARIES` to one or two libraries, or run with full list if budget allows.

```bash
export SERPER_API_KEY=...
export GEMINI_API_KEY=...
/Users/mtb/Omni-Studio/.venv/bin/python3 /Users/mtb/Omni-Studio/music_library_aggregator.py
```

- [ ] **Step 2: Verify results**

Run:
```bash
sqlite3 /Users/mtb/Omni-Studio/studio_crm.db "SELECT sub_library, COUNT(*) FROM leads WHERE source='MUSIC_LIBRARY_TARGET' GROUP BY sub_library;"
```

Expected: counts per sub-library; no duplicates on second run.

- [ ] **Step 3: Run twice to verify deduplication**

Run the script again with the same keys. Total count should not increase.

- [ ] **Step 4: Commit**

If any code changes were made during smoke testing, commit them.

---

## Plan Self-Review Checklist

- [ ] Spec coverage: every design section has a matching task.
- [ ] No placeholders: all code blocks are complete; no TODO/TBD.
- [ ] Type consistency: function names and signatures match across tasks.
- [ ] File paths: all paths are exact and inside `/Users/mtb/Omni-Studio/`.
- [ ] Verification: includes dry-run and live-key smoke tests.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-19-music-library-aggregator-plan.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — I execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

Which approach do you want?
