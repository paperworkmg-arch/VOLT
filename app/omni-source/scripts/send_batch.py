#!/usr/bin/env python3
"""
send_batch.py — walks through unsent cold DM drafts one at a time so
you can copy each into Instagram manually, then marks it as sent.

Usage:
    python3 send_batch.py            # default batch of 20
    python3 send_batch.py --count 30 # custom batch size
"""
import json
import sys
from pathlib import Path

BASE = Path.home() / "Omni-Studio"
DRAFTS_DIR = BASE / "Cold_Outreach_Drafts"
SENT_LOG = BASE / "coldlist_sent.json"


def load_sent():
    if SENT_LOG.exists():
        return set(json.loads(SENT_LOG.read_text()))
    return set()


def save_sent(sent):
    SENT_LOG.write_text(json.dumps(sorted(sent)))


def main():
    count = 20
    if "--count" in sys.argv:
        idx = sys.argv.index("--count")
        if idx + 1 < len(sys.argv):
            count = int(sys.argv[idx + 1])

    sent = load_sent()
    all_drafts = sorted(DRAFTS_DIR.glob("*.txt"))
    pending = [d for d in all_drafts if d.stem not in sent]

    if not pending:
        print("No pending drafts left. All caught up!")
        return

    batch = pending[:count]
    print(f"{len(pending)} drafts pending. Working through {len(batch)} now.\n")
    print("For each one: copy the DM text, paste it into Instagram, send it,")
    print("then press Enter here to mark it sent (or type 's' to skip).\n")

    for draft_path in batch:
        print("=" * 50)
        print(draft_path.read_text())
        print("=" * 50)
        action = input("Press Enter when sent, or 's' to skip: ").strip().lower()
        if action != "s":
            sent.add(draft_path.stem)
            save_sent(sent)
            print("Marked sent.\n")
        else:
            print("Skipped (will show again next run).\n")

    remaining = len(pending) - len([d for d in batch if d.stem in sent])
    print(f"\nBatch done. {remaining} drafts still pending.")


if __name__ == "__main__":
    main()
