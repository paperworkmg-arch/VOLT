# Music Library Aggregator — Operational Runbook

## Overview

- **Entry Point**: `agents/music_library_aggregator.py`
- **Database**: `data/studio_crm.db` (SQLite, leads table)
- **Config**: None currently (uses env vars + hardcoded CORE_LIBRARIES)
- **Dry Run**: `MLA_DRY_RUN=1` — uses fixture data, no API keys needed

## Quick Commands

### View Recent Targets
```bash
sqlite3 ~/Omni-Studio/data/studio_crm.db \
  "SELECT name, title, sub_library, linkedin_url, created_at FROM leads WHERE source='MUSIC_LIBRARY_TARGET' ORDER BY created_at DESC LIMIT 10;"
```

### Run Dry-Run
```bash
MLA_DRY_RUN=1 python3 ~/Omni-Studio/agents/music_library_aggregator.py
```

### Run Production
```bash
export SERPER_API_KEY=sk-xxx
export GEMINI_API_KEY=sk-xxx
python3 ~/Omni-Studio/agents/music_library_aggregator.py
```

### Export Targets to CSV
```bash
python3 ~/Omni-Studio/scripts/view_leads.py
```

### Dashboard (Volt)
```bash
open http://127.0.0.1:8500/app
# Leads section → Music Library Aggregator
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERPER_API_KEY` | Yes (prod) | — | Serper.dev API key for LinkedIn dorking |
| `GEMINI_API_KEY` | Yes (prod) | — | Google Gemini API key (falls back to `GOOGLE_API_KEY`) |
| `GEMINI_MODEL` | No | `gemini-3.5-flash` | Gemini model to use |
| `MLA_DRY_RUN` | No | `0` | Set `1` to use fixture data |

## Architecture

```
music_library_aggregator.py
  ├─ ensure_db()           → Creates leads table if missing
  ├─ build_dork(library)   → Constructs LinkedIn site: dork query
  ├─ dork_linkedin(client) → Hits Serper API (or loads fixture in dry-run)
  ├─ extract_targets()     → Gemini extracts named targets from search JSON
  ├─ save_targets()        → SQLite INSERT OR IGNORE (idempotent)
  └─ main()                → Loops CORE_LIBRARIES, runs pipeline per library
```

## Libraries Scanned

APM sub-labels: KPM, Bruton, Kosinus, Sonoton, Cezame, Liquid Cinema
UPM sub-labels: FirstCom, Chappell, Atmosphere, Elias Music, Chronic Trax, Capitol Studio Masters

## Troubleshooting

### No targets being inserted
1. Verify API keys: `echo $SERPER_API_KEY $GEMINI_API_KEY`
2. Check dry-run mode: `MLA_DRY_RUN=1 python3 ...` — should insert fixture targets
3. Check logs for `IntegrityError` (duplicate URLs)

### Database locked
1. WAL mode: `sqlite3 data/studio_crm.db "PRAGMA journal_mode;"`
2. If not WAL: `sqlite3 data/studio_crm.db "PRAGMA journal_mode=WAL;"`

### Gemini rate limited
- Retries up to 3 times with exponential backoff (5s → 20s → 60s)
- Logs warning on each retry

### Duplicate targets
- `linkedin_url` has UNIQUE constraint; re-runs are idempotent
- If somehow duplicated: `DELETE FROM leads WHERE source='MUSIC_LIBRARY_TARGET' AND linkedin_url = '...'`

## Scaling Limits

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Serper | 2,500 queries/month | ~200 per run (12 libs × ~17 queries) |
| Gemini | 60 req/min | Adequate for current scale |
| SQLite | Single-writer | WAL mode allows concurrent reads |

## Key Metrics

- `mla_targets_inserted_total` — New targets discovered per run
- `mla_targets_duplicate_total` — Duplicates skipped (idempotency working)

## Incident Response

### P1: Aggregator completely down
1. Check if server is running: `curl -s http://127.0.0.1:8500/api/system/health`
2. Check disk space: `df -h ~/Omni-Studio`
3. Check database integrity: `sqlite3 data/studio_crm.db "PRAGMA integrity_check;"`

### P2: Low confidence scores
- Review Gemini extraction prompt in `music_library_aggregator.py`
- Consider manual review of targets with confidence < 0.7
