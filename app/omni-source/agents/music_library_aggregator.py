"""
music_library_aggregator.py — Omni Studio module for APM/UPM sub-library A&R discovery.

Dependencies (install into .venv):
    pip install httpx google-genai pydantic

Environment:
    SERPER_API_KEY  - required for LinkedIn dorking
    GEMINI_API_KEY  - required for contact extraction
    GEMINI_MODEL    - optional; defaults to 'gemini-3.5-flash'
    MLA_DRY_RUN=1   - optional; uses fixtures instead of live APIs
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from typing import List

import httpx
from google import genai
from google.api_core import exceptions as google_exceptions
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger('Music-Library-Aggregator')

SERPER_API_KEY = os.getenv('SERPER_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash')
DRY_RUN = os.getenv('MLA_DRY_RUN', '0') == '1'

DB_PATH = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')

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

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = genai_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': TargetList,
                    'temperature': 0.1,
                },
            )
            data = json.loads(response.text)
            return data.get("targets", [])
        except google_exceptions.ResourceExhausted as e:
            wait = min(2 ** attempt * 5, 60)
            logger.warning(f"Gemini rate limit hit for {library_name}, retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Gemini extraction failed for {library_name}: {e}")
            return []
    logger.error(f"Gemini extraction failed for {library_name} after {max_retries} retries")
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
