# Music Library Aggregator Module — Design Spec

**Date:** 2026-07-19  
**Project:** Omni Studio  
**Author:** Kimi Code / superpowers:brainstorming

---

## 1. Goal

Build a self-contained Omni Studio module that continuously discovers A&R, Creative Director, and Catalog Manager contacts at APM Music and Universal Production Music sub-labels, then persists them as structured leads in the existing `studio_crm.db` for later outreach.

---

## 2. User Requirements (locked during brainstorming)

| Decision | Choice |
|----------|--------|
| Output destination | SQLite CRM leads table |
| Search/LLM stack | Gemini 1.5 Pro + Serper API |
| Trigger | Auto-run in `master_orchestrator.py` 15-minute cycle |
| Outreach generation | None — collect contacts only |
| CRM schema approach | Extend existing `leads` table |

---

## 3. Architecture

A single Python module runs as a first-class citizen in the orchestrator loop. It avoids brittle headless Google searches by routing LinkedIn dorks through Serper.dev, then uses Gemini's structured-output mode to turn raw SERP JSON into validated contact records. Records are inserted into the shared CRM with deduplication on `linkedin_url`.

---

## 4. Components

### 4.1 New File: `~/Omni-Studio/music_library_aggregator.py`
Responsibilities:
- Define the target sub-library roster (hardcoded core list + optional dynamic scrape via Playwright).
- Build LinkedIn dork queries for each sub-library.
- Call Serper.dev search API.
- Call Gemini to extract and filter contacts.
- Persist contacts to `studio_crm.db`.
- Emit logs compatible with `master_orchestrator.py`.

### 4.2 Schema Migration: `studio_crm.db`
Alter the existing `leads` table to support targets that lack email addresses:
- `email` becomes nullable.
- Add `sub_library TEXT` — which boutique library the target belongs to.
- Add `title TEXT` — job title.
- Add `linkedin_url TEXT UNIQUE` — deduplication key.
- Add `source TEXT` — value `"MUSIC_LIBRARY_TARGET"`.

### 4.3 Modified File: `~/Omni-Studio/view_leads.py`
- Surface `source` in the breakdown view.
- Display new columns for music-library targets when present.
- Keep existing lead display unchanged for non-music-library rows.

### 4.4 Modified File: `~/Omni-Studio/master_orchestrator.py`
Add `"Music Library Aggregator": "music_library_aggregator.py"` to the `SCRIPTS` dict.

### 4.5 Dependency: `httpx`
Install `httpx` into `.venv` for async Serper API calls.

---

## 5. Data Flow

1. **Bootstrap sub-libraries**
   - Start from a hardcoded core list (KPM, Bruton, Sonoton, Cezame, Liquid Cinema, FirstCom, Chappell, Atmosphere, Elias Music, Chronic Trax, Capitol Studio Masters).
   - Optionally scrape live label directories with Playwright; on failure, log warning and continue with hardcoded list.

2. **Run LinkedIn dorks via Serper**
   - Query per library: `site:linkedin.com/in/ ("A&R" OR "Creative Director" OR "Catalog Manager") "<library>"`
   - Request 10 results per query.
   - Use `httpx.AsyncClient` with retry/backoff.

3. **Synthesize with Gemini**
   - Feed raw Serper JSON to Gemini 1.5 Pro.
   - Enforce Pydantic schema `TargetList` via `response_schema`.
   - Prompt instructs Gemini to drop parent-company (APM/UPM) employees and keep boutique sub-library contacts only.

4. **Persist to CRM**
   - Insert each target into `leads`.
   - Deduplicate on `linkedin_url`.
   - Set `status = 'MUSIC_LIBRARY_TARGET'`, `source = 'MUSIC_LIBRARY_TARGET'`.
   - Leave `email` NULL when unknown.
   - Leave `city` NULL unless derivable from profile.

---

## 6. Error Handling & Resilience

| Failure | Behavior |
|---------|----------|
| `GEMINI_API_KEY` or `SERPER_API_KEY` missing | Log fatal error and exit with non-zero status so orchestrator records failure. |
| Serper API rate-limit / HTTP error | Log library-level error, sleep briefly, continue to next library. |
| Gemini timeout or malformed response | Log error, continue to next library. |
| Playwright label-page scrape fails | Log warning, fall back to hardcoded core list. |
| Duplicate `linkedin_url` | Silently skip insert (SQLite unique constraint). |
| Empty Serper results for a library | Log info, no inserts. |

---

## 7. Testing Strategy

- **Unit tests** for dork string construction and Serper payload shape.
- **Mocked Gemini test** using a fixture SERP JSON file and verifying structured output parsing.
- **DB integration test** confirming schema migration, insert, and deduplication.
- **Dry-run mode** in the module: when env `MLA_DRY_RUN=1`, use fixture data instead of live APIs.

---

## 8. Configuration

All configuration lives in environment variables (consistent with existing code):

| Variable | Purpose |
|----------|---------|
| `SERPER_API_KEY` | Serper.dev API key |
| `GEMINI_API_KEY` | Google AI API key |
| `MLA_DRY_RUN` | Optional; `1` disables live API calls and uses fixtures |

---

## 9. Logging

Use Python `logging` with the same format as `scraper.py`:
```
%(asctime)s | %(levelname)s | %(message)s
```
Log entries must be single-line so `master_orchestrator.py` can prefix and forward them cleanly.

---

## 10. Security & Compliance Notes

- Serper.dev is a paid, terms-compliant proxy for Google search results; it avoids direct scraping of LinkedIn or Google.
- LinkedIn profile URLs are public data.
- No email extraction from LinkedIn is attempted; only names, titles, and public profile URLs are stored.
- API keys must never be committed; loaded via environment variables only.

---

## 11. Future Extensions (out of scope)

- Generate pitch drafts per target and write to `Outbound_Pitches/`.
- Auto-send cold emails via existing Gmail integration.
- Add sub-library portfolio mapping (genre-based placement).
- Refresh stale targets on a slower cadence.

---

## 12. Acceptance Criteria

- [ ] `music_library_aggregator.py` runs without errors in the orchestrator cycle when API keys are present.
- [ ] At least one target from each core sub-library is inserted on first run.
- [ ] Duplicate runs do not create duplicate rows.
- [ ] `view_leads.py` shows a `MUSIC_LIBRARY_TARGET` source breakdown.
- [ ] Missing API keys produce a clear, single-line fatal log.
