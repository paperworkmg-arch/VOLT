#!/usr/bin/env python3
"""
Import Volt Records catalog tracks from tracks.json into the vault.

Usage:
    python import_tracks.py [--reset] [--json path/to/tracks.json]
"""
import json
import sys
import argparse
from pathlib import Path

# Add parent to path for vault import
sys.path.insert(0, str(Path(__file__).parent))
from vault import Vault


def main():
    parser = argparse.ArgumentParser(description="Import tracks.json into vault")
    parser.add_argument("--json", default="./tracks.json", help="Path to tracks.json")
    parser.add_argument("--db", default="./vault.db", help="Vault DB path")
    parser.add_argument("--reset", action="store_true", help="Clear existing catalog before import")
    args = parser.parse_args()

    tracks_path = Path(args.json)
    if not tracks_path.exists():
        print(f"ERROR: tracks.json not found at {tracks_path}")
        sys.exit(1)

    print(f"Reading {tracks_path}...")
    with open(tracks_path, "r", encoding="utf-8") as f:
        tracks = json.load(f)

    print(f"Loaded {len(tracks)} tracks from JSON")

    vault = Vault(args.db)
    vault.init_schema()

    if args.reset:
        print("Clearing existing catalog...")
        vault.clear_catalog()

    count = vault.import_catalog_tracks(tracks, source_file=str(tracks_path))
    print(f"Imported {count} tracks into vault")

    summary = vault.get_catalog_summary()
    print("\nCatalog Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    top = vault.get_top_prospects(3)
    print("\nTop 3 Prospects:")
    for t in top:
        print(f"  {t['track_name']} — HPI {t['hpi']:.2f} ({t['verdict_bucket']})")

    print(f"\nVault DB: {Path(args.db).resolve()}")


if __name__ == "__main__":
    main()
