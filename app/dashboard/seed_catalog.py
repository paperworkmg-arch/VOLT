#!/usr/bin/env python3
"""Seed the vault catalog DB from the static tracks.json if the catalog is empty."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
TRACKS_JSON = BASE.parent / "volt-dashboard" / "src" / "data" / "tracks.json"
VAULT_DIR = BASE / "data" / "vault"
sys.path.insert(0, str(VAULT_DIR))

from vault import Vault

vault = Vault(str(VAULT_DIR / "vault.db"))
vault.init_schema()

summary = vault.get_catalog_summary()
if summary.get("total_tracks", 0) > 0:
    print(f"Catalog already has {summary['total_tracks']} tracks — skipping seed.")
    sys.exit(0)

if not TRACKS_JSON.exists():
    print(f"tracks.json not found at {TRACKS_JSON} — skipping seed.")
    sys.exit(0)

with open(TRACKS_JSON) as f:
    tracks = json.load(f)

count = vault.import_catalog_tracks(tracks, source_file="tracks.json")
print(f"Seeded vault DB with {count} tracks from tracks.json.")
