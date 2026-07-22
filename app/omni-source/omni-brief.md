# OMNI-STUDIO: Comprehensive Content Brief
**Generated:** 2026-07-20
**Purpose:** Complete system documentation for dashboard redesign

---

## TABLE OF CONTENTS
1. [System Overview](#system-overview)
2. [Master Loop & Orchestration](#1-master-loop--orchestration)
3. [Watchdog & Monitoring](#2-watchdog--monitoring)
4. [Lead Pipeline & Outreach](#3-lead-pipeline--outreach)
5. [Email & Communication](#4-email--communication)
6. [Audio & Catalog Analysis](#5-audio--catalog-analysis)
7. [Finance & Income Tracking](#6-finance--income-tracking)
8. [Agent Swarm & AI](#7-agent-swarm--ai)
9. [Database & Storage](#8-database--storage)
10. [External Integrations](#9-external-integrations)
11. [API Endpoint Reference](#10-api-endpoint-reference)
12. [Environment Variables Master List](#11-environment-variables-master-list)
13. [File Map](#12-file-map)

---

## System Overview

Omni-Studio is an enterprise-grade, local-first command center for Volt Records (Atlanta, GA), a recording studio founded by Grammy-nominated producer Mykel T. Brooks. The system unifies:

- **Autonomous lead generation** (web scraping, Google Alerts, Instagram cold outreach)
- **AI-powered artist engagement** (inbound email agent, follow-up nudge engine, press pitch generation)
- **Income reconciliation** (payment notification scanning, gate code generation)
- **Studio operations** (booking calendar, invoice generation, session confirmation)
- **Audio asset management** (sample library scanning, key/tempo analysis, SFZ kit building)
- **Music catalog analytics** (track scoring via HPI, verdict bucketing, prospect ranking)
- **Multi-agent AI swarm** (Atlas, Scout, Forge, Pulse, Echo, Harmony agents)
- **Kimi/Omi ambient capture** (daily transcript extraction into music IP, CRM notes, SOPs)
- **FastAPI dashboard** (web UI on port 8500, accessible on LAN)
- **GODMODE** (Claude Code multi-agent development framework with 50+ skills)

**Tech stack:** Python 3, FastAPI, SQLite (aiosqlite), APScheduler, Ollama (qwen3:14b local LLM), Kimi/Moonshot API, Gemini API, Google Drive API, Playwright, librosa, watchdog.

---

## 1. Master Loop & Orchestration

### Shell Scripts

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/master_loop.sh` | Cron-scheduled master cycle: scrapes leads, reconciles income, runs inbound agent, sends AR pitches. Runs every 15 min via launchd. |
| `/Users/mtb/Omni-Studio/run_pipeline.sh` | One-shot pipeline: runs scraper, fetches emails, launches watchdog. |
| `/Users/mtb/Omni-Studio/verify_and_run.sh` | Pre-flight checker: verifies required files exist before launching pipeline. |
| `/Users/mtb/Omni-Studio/studio_core.sh` | Network discovery: mounts SMB share to remote Mac (SuperMac at 10.0.0.250), SSHes into it, maps file systems, then feeds raw telemetry to Qwen3:14b via opencode for strategic analysis. |

### Python Orchestrators

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/core/master_orchestrator.py` | Long-running daemon that cycles through 5 scripts every 15 minutes: Scraper, Outbound Pitcher, Inbound AI Agent, Income Watchdog, Music Library Aggregator. Uses .venv Python. |
| `/Users/mtb/Omni-Studio/core/autopilot.py` | Autonomous job scheduler with retry logic, exponential backoff, and its own SQLite DB (`autopilot.db`). Default jobs: Lead Scraper (15min), Income Watchdog (10min), Inbound Agent (5min), AR Pitcher (20min), Sample Scanner (60min, disabled). Exposes `Autopilot` singleton class. |
| `/Users/mtb/Omni-Studio/dashboard/scheduler.py` | APScheduler-based cron task executor for the dashboard. Parses cron expressions, executes tasks by calling assigned LLM agents, records results in `task_results` table. |

**Key functions:**
- `Autopilot.start()` / `Autopilot.stop()` -- controls the autopilot scheduler
- `Autopilot.run_job_now(name)` -- triggers immediate execution of a named job
- `_execute_job(name, script, timeout, max_retries)` -- runs a script with retry logic
- `run_scheduled_task(task_id, name, agent)` -- dashboard scheduler task executor
- `sync_scheduled_tasks()` / `sync_schedules()` -- reloads cron jobs from DB

**Database tables:**
- `autopilot.db`: `jobs` (name, script, schedule, enabled, retries, timeout, last_run, last_status, run_count, fail_count), `runs` (job_name, started_at, finished_at, status, output, duration_ms, retry_count)

**Environment variables:** None directly (reads DB).

**Connections:** Orchestrator calls into `integrations/scraper.py`, `scripts/income_watchdog.py`, `agents/inbound_agent.py`, `integrations/send_ar_pitches.py`, `agents/music_library_aggregator.py`. Autopilot integrates with the FastAPI dashboard for status/control.

---

## 2. Watchdog & Monitoring

### Shell Scripts

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/watchdog.sh` | Filesystem watchdog daemon. Polls `Incoming_Leads/` every 5 seconds. When a new lead file appears, it sends it to Ollama (qwen3:14b) to generate a Grammy-nominated booking pitch. Moves processed leads to `Closed_Deals/` and writes pitches to `Outbound_Pitches/`. Sends macOS notifications. Uses PID file to prevent duplicates. |
| `/Users/mtb/Omni-Studio/status.sh` | Status checker: queries `launchctl` for `com.voltrecords.alerts` and `com.voltrecords.studioagent` services. Shows last 5 lines of alert and agent logs. |

### Python Watchdogs

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/scripts/alerts_watcher.py` | Google Alerts RSS feed reader. Polls configured feed URLs every 15 minutes. Parses Atom XML entries, extracts new leads, writes them to `Incoming_Leads/`. Tracks seen entries in `alerts_seen.json`. |
| `/Users/mtb/Omni-Studio/dashboard/daw_watcher.py` | DAW export watcher using `watchdog` library. Monitors `~/Music/Logic/` and `~/Music/Logic/Bounces/` for new audio files. Auto-uploads to Google Drive and sends email notification. Maintains state in `daw_watcher_state.json`. |
| `/Users/mtb/Omni-Studio/dashboard/omni.py` (Disk Cleaner) | Built-in disk cleanup: monitors usage against 700GB limit. Cleans `__pycache__`, `.log`, `.tmp`, `.cache`, `.bak`, `.old` files older than 30 days. Also cleans old backups (keeps last 5). Scheduled as "Disk Cleaner" cron task. |

**Key functions:**
- `DAWExportHandler.on_created(event)` / `on_moved(event)` -- detects new Logic Pro exports
- `DAWWatcher.start()` / `stop()` -- controls the file observer
- `run_disk_cleaner()` -- returns usage report with actions taken
- `alert_watcher.run_once(seen, feeds)` -- one poll cycle for Google Alerts

**Connections:** Watchdog writes to `Incoming_Leads/` which is consumed by `watchdog.sh` and `studio_agent.py`. DAW watcher calls `google_drive.upload_to_drive()` and `email_notifier.send_export_notification()`.

---

## 3. Lead Pipeline & Outreach

### Lead Sources

| File | Source Type |
|------|------------|
| `/Users/mtb/Omni-Studio/integrations/scraper.py` | Playwright headless browser scraping Yahoo search for "recording artist" + city + "@gmail.com" on Instagram/SoundCloud. Covers LA, Atlanta, NYC, Chicago, Miami, Houston, Toronto, London, Nashville. Saves to `studio_crm.db` leads table. |
| `/Users/mtb/Omni-Studio/scripts/alerts_watcher.py` | Google Alerts RSS feeds (configurable in `data/alert_feeds.txt`). Writes lead files to `Incoming_Leads/`. |
| `/Users/mtb/Omni-Studio/agents/instagram_coldlist.py` | Instagram CSV parser: reads exported follower CSVs, extracts usernames via regex, generates cold DMs using Ollama (qwen3:14b). Outputs to `Cold_Outreach_Drafts/`. Tracks contacted users in `coldlist_contacted.json`. |
| `/Users/mtb/Omni-Studio/agents/music_library_aggregator.py` | LinkedIn dorking via Serper API + Gemini extraction for A&R contacts at APM/UPM sub-libraries (KPM, Bruton, Sonoton, etc.). Stores targets in `studio_crm.db` leads table with status `MUSIC_LIBRARY_TARGET`. |

### Pitch Generation

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/watchdog.sh` | Generates booking pitches via Ollama. Includes Grammy nomination, 1 Free Hour promo, room pricing ($90/hr A Room, $75/hr B Room), deal math. |
| `/Users/mtb/Omni-Studio/agents/studio_agent.py` | Advanced Python lead processor. Extracts facts via LLM (budget, hours, genre, premium gear, engineer needs, deadlines). Computes deal structure with bulk discounts. Writes structured pitches with risk assessment (Green/Yellow/Red). |
| `/Users/mtb/Omni-Studio/agents/ghost_followup.py` | Follow-up nudge engine. Scans `Outbound_Pitches/` for pitches older than threshold (default 0.01hr for testing, 48hr for production). Generates casual follow-up text via Ollama. Appends to pitch file. Skips artists already in `Closed_Deals/`. |
| `/Users/mtb/Omni-Studio/scripts/press_pitch_generator.py` | PR pitch generator for national media. Reads `national_media_contacts.csv` (150 outlets: Complex, XXL, TechCrunch, Billboard, Rolling Stone, etc.). Generates tailored pitches per outlet type using Ollama. Includes founder bio, Grammy credentials, and local asset inventory. |
| `/Users/mtb/Omni-Studio/scripts/generate_national_contacts.py` | Generates the `national_media_contacts.csv` with 150 curated media contacts across music, tech, culture, business, and syndicated sectors. |

### Outreach Sending

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/integrations/send_ar_pitches.py` | Sends A&R pitches via Gmail SMTP. Reads pitches from `Outbound_Pitches/`, extracts email from corresponding `Closed_Deals/` entry, sends email, moves to `Contacted_Leads/`. 15-second delay between sends. |
| `/Users/mtb/Omni-Studio/integrations/send_press_pitches.py` | Sends PR pitches via Gmail SMTP. Parses `CONTACT EMAIL:` and `SUBJECT:` from pitch files. Moves sent pitches to `Sent_Pitches/`. |
| `/Users/mtb/Omni-Studio/integrations/send_emails.py` | Generic outbound email queue flusher. Reads from `/Users/mtb/ready_to_send/`, parses TO/SUBJECT/BODY fields, sends via SMTP, archives sent files. (Has syntax errors -- appears to be a draft.) |
| `/Users/mtb/Omni-Studio/scripts/send_batch.py` | Manual Instagram DM send assistant. Walks through cold DM drafts one at a time, displays content, waits for user to copy/paste into Instagram, marks as sent. Configurable batch size. |

### Lead Viewing

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/scripts/view_leads.py` | CLI viewer for `studio_crm.db`. Shows lead counts by status (SCRAPED, PITCHED, PENDING VERIFICATION, CLOSED, MUSIC_LIBRARY_TARGET), lists recent 900 leads, and shows music library targets separately. |
| `/Users/mtb/Omni-Studio/scripts/dashboard.py` | ASCII dashboard: counts files in Incoming_Leads, Closed_Deals, Outbound_Pitches, Press_Pitches. Extracts dollar values from pitch files for pipeline revenue calculation. |

**Key pricing constants:**
- A Room: $90/hr (Neumann/Tube-Tech chains)
- B Room: $75/hr (Production & Mixing)
- Engineer surcharge: $35/hr
- Bulk discount: 10% for 12+ hours
- First Hour Free promotional offer

**Directory flow:**
```
Incoming_Leads/ -> (watchdog/studio_agent) -> Outbound_Pitches/ -> (send_ar_pitches) -> Contacted_Leads/
                                                                                   -> Closed_Deals/
Press_Pitches/ -> (send_press_pitches) -> Sent_Pitches/
Cold_Outreach_Drafts/ -> (send_batch manual) -> Instagram DMs
Confirmed_Sessions/ (income_watchdog output)
```

---

## 4. Email & Communication

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/agents/inbound_agent.py` | Autonomous inbound email responder. Connects to Gmail IMAP (paperworkmg@gmail.com), scans for UNSEEN emails, filters out system/spam senders (Square, Zelle, Venmo, GitHub, etc.), extracts body, generates AI response via Ollama (qwen3:14b) as Mykel T. Brooks persona, sends reply via SMTP. 60-second timeout on LLM calls. |
| `/Users/mtb/Omni-Studio/dashboard/email_notifier.py` | Email notification module for DAW exports. Sends via Gmail SMTP when new Logic Pro exports are detected. Saves notification history to `data/notifications.json` (last 100). |
| `/Users/mtb/Omni-Studio/integrations/gmail_client.py` | Gmail OAuth2 client. Full-access (`https://mail.google.com/`). Stores credentials in `config/token.pickle`. Refreshes expired tokens. |
| `/Users/mtb/Omni-Studio/integrations/fetch_emails.py` | Simple IMAP email fetcher. Reads last 10 unread emails, saves to `agent_email_inbox/`. |
| `/Users/mtb/Omni-Studio/integrations/send_emails.py` | Generic outbound queue flusher (draft/broken). |

**External integrations:** Gmail IMAP/SMTP (paperworkmg@gmail.com), Gmail OAuth2 API.

**Environment variables:**
- `EMAIL_USER`, `EMAIL_PASS` (for send_emails.py / fetch_emails.py)
- `NOTIFY_EMAIL` (for email_notifier.py, defaults to paperworkmg@gmail.com)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`

**Connections:** Inbound agent is called by master_loop.sh. Email notifier is called by daw_watcher.py. Gmail client is used by audit_missed_funds.py.

---

## 5. Audio & Catalog Analysis

### Sample Library System

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/dashboard/sample_library.py` | SQLite-backed sample database. Tables: `samples` (path, filename, key, mode, tempo, duration, sample_type, tags, notes, drive_id/url), `scan_runs`, `drive_sync`, `kits`, `kit_samples`. Provides search, stats, upsert, tag/note management. |
| `/Users/mtb/Omni-Studio/dashboard/sample_scanner.py` | Audio file scanner. Walks ~/Music/Logic, ~/Music/Ableton, ~/Music/Loose Imports, ~/Desktop, ~/Documents, ~/Downloads. Detects key via Krumhansl-Schmuckler chromagram correlation (librosa). Classifies samples as one-shot/loop/full-track/export/project-sample. Quick scan (metadata only) and full scan (with key/tempo). |
| `/Users/mtb/Omni-Studio/dashboard/sampler_engine.py` | Universal sampler kit builder. Creates drum or chromatic kits from samples. Maps MIDI notes (General MIDI drum map for drums, chromatic spread for melodic). Exports as SFZ (universal sampler format) + JSON metadata + sample files, zipped. Can upload to Google Drive. |
| `/Users/mtb/Omni-Studio/dashboard/google_drive.py` | Google Drive upload module. Uses service account (`dashboard/data/service-account.json`). Creates/finds folders, uploads files with MIME type detection, returns shareable URL. |
| `/Users/mtb/Omni-Studio/dashboard/daw_watcher.py` | Monitors Logic Pro export folders for new audio. Auto-uploads to Drive, sends email notification. |

### Catalog Analytics (Vault)

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/data/vault/vault.py` | Full-featured SQLite DAO with FTS5 search. Manages: sessions, raw transcript entries, daily batches, Kimi extractions, music IP, CRM notes, SOPs, tags/taggings, and **catalog tracks** (Volt Records). Catalog features: HPI scoring, verdict bucketing (ACQUIRE/PITCH/LICENSE/ANALYZE), key distribution, analytics views. |
| `/Users/mtb/Omni-Studio/data/vault/schema.sql` | Complete database schema (383 lines). FTS5 virtual tables for all entity types. WAL mode. Views: `v_daily_summary`, `v_recent_activity`, `v_catalog_summary`, `v_key_distribution`, `v_bucket_distribution`. |
| `/Users/mtb/Omni-Studio/data/vault/import_tracks.py` | CLI tool to import catalog tracks from `tracks.json` into vault. Shows summary stats and top 3 prospects. |

### Cross-Render Pipeline

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/core/cross_render.py` | Text-to-music-to-stems-to-kit pipeline. Stages: generate (placeholder audio) -> separate stems -> catalog samples -> build kit -> export SFZ. Tracks progress in `cross_render.db` `renders` table. |

### Studio Operations

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/core/check_calendar.py` | Booking conflict checker. Reads `studio_calendar.json`, checks for overlapping bookings in A Room or B Room. Returns availability status. |
| `/Users/mtb/Omni-Studio/core/invoice.py` | Invoice generator. CLI: `invoice.py [ArtistName] [Room A/B] [Hours]`. Calculates subtotal and 50% deposit. Saves to `{artist}_invoice_draft.txt`. |

**Database tables (sample library -- `samples.db`):**
- `samples`: id, path (UNIQUE), filename, directory, extension, size_bytes, size_mb, modified_at, file_hash, sample_type, key, mode, key_full, tempo, duration, analyzed, tags (JSON), notes, drive_id, drive_url, synced_at, created_at, updated_at
- `scan_runs`: id, files_found, files_analyzed, duration_seconds, status, started_at, completed_at
- `drive_sync`: id, sample_id, drive_id, drive_url, folder, synced_at
- `kits`: id, name, description, layout_type, export_path, drive_url, created_at, updated_at
- `kit_samples`: id, kit_id, sample_id, midi_note, lo_note, hi_note, pitch_center, velocity_lo, velocity_hi, root_key, fine_tune, volume_db

**Database tables (vault -- `vault.db`):**
- `sessions`: session_id, device_info
- `raw_entries`: session_id, transcript, timestamp, source_ip
- `transcript_batches`: batch_date, content, entry_count, char_count, status
- `extractions`: batch_id, model, raw_response, processing_time_ms, status
- `music_ip`: extraction_id, title, category, content, mood, tags, confidence
- `crm_notes`: extraction_id, deal_name, contact_name, company, deal_stage, notes, action_items, follow_up_date, deal_value, currency, confidence
- `sops`: extraction_id, title, category, content, prerequisites, related_tools, confidence
- `tags`, `taggings`: polymorphic tag system
- `catalog_tracks`: track_name, bpm, key, brightness, energy_density, alpha, structural_velocity, market_modularity, hpi, verdict, verdict_bucket, source_file

---

## 6. Finance & Income Tracking

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/scripts/income_watchdog.py` | Payment detection agent. Scans Gmail IMAP for unread emails from CashApp (cash@square.com), Zelle (no-reply@zellepay.com), Venmo (venmo@venmo.com). Matches payment notifications against active pitches in `Outbound_Pitches/`. On match: generates gate code (`*XXXX#` format), moves pitch to `Confirmed_Sessions/` with "CONFIRMED & PAID" status. |
| `/Users/mtb/Omni-Studio/scripts/audit_missed_funds.py` | Historical payment auditor. Searches Gmail for payment receipts from the last 6 months via Gmail API. Extracts sender names from "sent you" / "paid you" snippets. Creates leads in `studio_crm.db` with status "PENDING VERIFICATION". (Has code issues -- appears to reference `service` object without initializing Gmail API.) |
| `/Users/mtb/Omni-Studio/scripts/dashboard.py` | ASCII revenue dashboard. Extracts dollar values from pitch files using regex, aggregates total pipeline value, shows per-artist projected revenue. |
| `/Users/mtb/Omni-Studio/core/invoice.py` | Invoice generator with deposit calculation (50% upfront). |

**Key financial data points:**
- A Room rate: $90/hr
- B Room rate: $75/hr
- Engineer surcharge: $35/hr
- Bulk discount: 10% on 12+ hours
- Payment methods: CashApp, Zelle, Venmo, Apple Pay
- Gate code format: `*XXXX#`

**Connections:** Income watchdog is called by master_loop.sh. Dashboard revenue data feeds the ASCII dashboard. Invoice generator is standalone CLI.

---

## 7. Agent Swarm & AI

### Dashboard Agent System

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/dashboard/swarm.py` | Multi-agent orchestrator. 5 agents with distinct roles and LLM models. Decomposes objectives into subtasks via Atlas, dispatches in parallel (max 3 concurrent), synthesizes results. |
| `/Users/mtb/Omni-Studio/dashboard/omni.py` | Monolithic single-file dashboard (1252 lines). Contains all of: config, DB init, LLM client, scheduler, swarm, web bridge, autonomous executor, Kimi daily pipeline, vault tools, audio ingestion watcher, disk cleaner, sample library APIs, kit APIs, Kimi bridge APIs, Omi webhook. |
| `/Users/mtb/Omni-Studio/dashboard/kimi_client.py` | CLI client for Kimi app to interact with Omni-Studio. Commands: status, swarm, agent, chat, queue, complete. |

### Agent Definitions

| Agent | Role | Model | Description |
|-------|------|-------|-------------|
| Atlas | Orchestrator | kimi-for-coding/k2p7 | Central coordinator -- decomposes objectives, dispatches tasks |
| Scout | Researcher | kimi-for-coding/kimi-k2-thinking | Deep research, data gathering, analysis |
| Forge | Builder | kimi-for-coding/k2p7 | Writes code, builds systems, deploys |
| Pulse | Monitor | kimi-for-coding/kimi-for-coding-highspeed | Watches schedules, checks health, pushes alerts |
| Echo | Comms | xai/grok-3-mini | Handles email, notifications, external comms |
| Harmony | Studio | kimi-for-coding/kimi-for-coding-highspeed | Audio analysis, metadata, mixing (omni.py only) |

### LLM Provider Configuration

| Provider | Base URL | Format |
|----------|----------|--------|
| Kimi | https://api.kimi.com/coding | Anthropic |
| OpenRouter | https://openrouter.ai/api/v1 | OpenAI |
| Ollama | http://localhost:11434/v1 | OpenAI |
| xAI | https://api.x.ai/v1 | OpenAI |
| Google | generativelanguage.googleapis.com | Google |

### Standalone AI Agents

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/agents/inbound_agent.py` | Autonomous email responder (Ollama qwen3:14b). |
| `/Users/mtb/Omni-Studio/agents/studio_agent.py` | Lead processor with fact extraction, deal computation, and pitch generation (Ollama qwen3:14b). |
| `/Users/mtb/Omni-Studio/agents/ghost_followup.py` | Follow-up nudge generator (Ollama qwen3:14b). |
| `/Users/mtb/Omni-Studio/agents/instagram_coldlist.py` | Cold DM generator (Ollama qwen3:14b via HTTP API). |
| `/Users/mtb/Omni-Studio/agents/music_library_aggregator.py` | LinkedIn contact extractor (Serper + Gemini). |

### Kimi/Omi Bridge

| File | Purpose |
|------|---------|
| `/Users/mtb/Omni-Studio/dashboard/bridge.py` | Bidirectional Kimi <-> Omni-Studio bridge. Routes swarm, agent, chat, and status tasks. File-based task queue (pending/completed JSON files). |
| `/Users/mtb/Omni-Studio/dashboard/omi_kimi_bridge.py` | Omi ambient transcript receiver. Receives transcripts via webhook, appends to daily log files, then processes daily batch through Kimi 128k for structured extraction (music IP, CRM notes, SOPs). |

### Kimi Daily Pipeline (in omni.py)

Full agentic pipeline: pull context (vault + CRM) -> parallel extraction (3 specialized agents: music IP, CRM notes, SOPs) -> vault storage -> optional Slack summary -> database persistence.

**Key functions:**
- `swarm.run(objective)` / `swarm_run(objective)` -- execute a swarm run
- `call_llm(provider, model, messages, system)` -- unified LLM call across all providers
- `autonomous_execute(objective, max_steps)` -- plan-and-execute autonomous agent
- `webbridge_task(objective)` -- web research agent (DuckDuckGo search + fetch + synthesize)
- `kimi_daily_process(transcript)` -- full Kimi daily extraction pipeline
- `tool_create_document()`, `tool_send_slack_summary()`, `tool_vault_store()`, `tool_vault_search()`

---

## 8. Database & Storage

### Database Inventory

| Database | Location | Tables | Purpose |
|----------|----------|--------|---------|
| `dashboard.db` | `dashboard/data/dashboard.db` | tasks, task_results, agents, plugins, sites, swarm_runs, activity_log | Core dashboard state |
| `samples.db` | `dashboard/data/samples.db` | samples, scan_runs, drive_sync, kits, kit_samples | Sample library and sampler kits |
| `contacts.db` | `dashboard/data/contacts.db` | contacts (name, email, phone, company, role, source, status, tags, notes) | CRM contacts |
| `autopilot.db` | `data/autopilot.db` | jobs, runs | Autopilot job scheduling |
| `studio_crm.db` | `studio_crm.db` (project root) | leads (id, name, email, city, status, gate_code, sub_library, title, linkedin_url, source) | Lead pipeline CRM |
| `cross_render.db` | `data/cross_render.db` | renders (prompt, status, stages, kit_id) | Cross-render pipeline state |
| `kimi_daily.db` | `dashboard/data/kimi_daily.db` | extractions, vault | Kimi daily extraction results |
| `vault.db` | `data/vault/vault.db` | sessions, raw_entries, transcript_batches, extractions, music_ip, crm_notes, sops, tags, taggings, catalog_tracks (+ FTS5 tables + views) | Full vault with ambient transcripts, entities, and catalog analytics |

### File-Based Storage

| Directory | Purpose |
|-----------|---------|
| `Incoming_Leads/` | Raw lead files (text) |
| `Closed_Deals/` | Processed leads with lead data |
| `Outbound_Pitches/` | Generated pitches awaiting sending |
| `Contacted_Leads/` | Pitches that have been emailed |
| `Confirmed_Sessions/` | Paid/confirmed artist sessions |
| `Press_Pitches/` | Generated PR pitches |
| `Sent_Pitches/` | Sent PR pitches |
| `Cold_Outreach_Drafts/` | Instagram cold DM drafts |
| `data/alert_feeds.txt` | Google Alerts feed URLs |
| `data/alerts_seen.json` | Dedup tracking for alert entries |
| `data/coldlist_contacted.json` | Dedup tracking for Instagram outreach |
| `data/coldlist_sent.json` | Sent DM tracking |
| `data/studio_calendar.json` | Studio booking calendar |
| `logs/` | System logs (master_engine, watchdog, agent, alerts_watcher, etc.) |
| `dashboard/data/bridge/` | Kimi task queue (pending/complete JSON) |
| `dashboard/data/omi_logs/` | Omi transcript daily logs |
| `dashboard/data/notifications.json` | Email notification history |
| `dashboard/data/daw_watcher_state.json` | DAW watcher processed file tracking |
| `dashboard/data/sampler-exports/` | SFZ kit export staging area |
| `dashboard/ingest_folder/` | Audio ingestion watch folder |
| `dashboard/processed_folder/` | Processed audio archive |
| `data/vault/` | Vault database and import tools |

### Key Dashboard DB Schema

**tasks** table:
- id, name, type (manual/scheduled), status, progress, result, agent, scheduled_cron, enabled, created_at, updated_at

**agents** table:
- id, name, role, model, status (idle/working/paused), tasks_completed, last_active, config

**plugins** table:
- id, name (UNIQUE), type, enabled, config, last_run, result
- Seeded: "Financial Data", "Economic Calendar", "Music Industry", "Weather"

**activity_log** table:
- id, source, message, level, created_at

**swarm_runs** table:
- id, objective, status, agents_used, started_at, completed_at, result

---

## 9. External Integrations

| Integration | Used By | API/Protocol |
|-------------|---------|--------------|
| **Ollama** (local LLM) | All agents, watchdog | HTTP API `localhost:11434/api/generate` (qwen3:14b) |
| **Kimi/Moonshot** | Swarm, scheduler, omi_kimi_bridge | Anthropic format via `api.kimi.com/coding`; Moonshot via `api.moonshot.cn/v1` (128k context) |
| **Google Gemini** | Music Library Aggregator, swarm | `generativelanguage.googleapis.com` |
| **OpenRouter** | Swarm | `openrouter.ai/api/v1` |
| **xAI (Grok)** | Echo agent | `api.x.ai/v1` |
| **Serper.dev** | Music Library Aggregator | `google.serper.dev/search` (LinkedIn dorking) |
| **Gmail SMTP/IMAP** | Inbound agent, A&R pitcher, press pitcher, email notifier | `smtp.gmail.com:587` / `imap.gmail.com` (paperworkmg@gmail.com) |
| **Gmail OAuth2** | Gmail client, audit_missed_funds | Google API (`mail.google.com/` scope) |
| **Google Drive** | Sample library, DAW watcher, sampler engine | Drive API v3 via service account |
| **Playwright** | Web scraper | Headless Firefox browser |
| **DuckDuckGo** | Web bridge (omni.py) | `api.duckduckgo.com` |
| **Slack** | Kimi daily pipeline | Webhook URL (`SLACK_WEBHOOK_URL`) |
| **macOS notifications** | Watchdog, inbound agent | `osascript` display notification |
| **launchctl** | Status checker | `com.voltrecords.alerts`, `com.voltrecords.studioagent` |
| **SMB/CIFS** | studio_core.sh | Network mount to remote Mac (10.0.0.250) |
| **Google APIs (Calendar, etc.)** | config/.env | Calendar link configured |

---

## 10. API Endpoint Reference

All endpoints are on the FastAPI app (port 8500).

### Pages
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard HTML (Jinja2 template) |

### Task API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tasks` | List all tasks |
| POST | `/api/tasks` | Create task (name, type, agent, cron) |
| POST | `/api/tasks/{id}/run` | Execute task immediately |
| POST | `/api/tasks/{id}/toggle` | Enable/disable task |

### Agent API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/agents` | List all agents |
| POST | `/api/agents/{id}/status` | Update agent status |
| POST | `/api/agents/{id}/toggle` | Toggle agent active/paused |

### Swarm API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/swarm/runs` | List swarm runs |
| POST | `/api/swarm/run` | Execute swarm objective |
| GET | `/api/swarm/status` | Check if swarm is running |

### Plugin API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/plugins` | List plugins |
| GET | `/api/plugins/registered` | List registered plugins |
| POST | `/api/plugins/{name}/run` | Execute plugin |

### Chat API
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Direct LLM chat (message, provider, model) |

### Sites API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sites` | List sites |
| POST | `/api/sites` | Create site (name, template) |

### Sample Library API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/samples` | Search samples (q, key, tempo_min/max, sample_type, directory, limit, offset) |
| GET | `/api/samples/stats` | Library statistics |
| GET | `/api/samples/keys` | All detected keys |
| GET | `/api/samples/directories` | All directories |
| GET | `/api/samples/unanalyzed` | Samples needing analysis |
| GET | `/api/samples/scan-history` | Past scan results |
| GET | `/api/samples/{id}` | Sample detail |
| POST | `/api/samples/{id}/tags` | Update tags |
| POST | `/api/samples/{id}/notes` | Update notes |
| POST | `/api/samples/scan` | Start audio scan |
| POST | `/api/samples/analyze` | Analyze key/tempo |
| POST | `/api/samples/export` | Export to Google Drive |

### Sampler / Kit API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/kits` | List kits |
| POST | `/api/kits` | Create kit (name, description, layout_type, sample_ids) |
| GET | `/api/kits/{id}` | Kit detail with samples |
| DELETE | `/api/kits/{id}` | Delete kit |
| POST | `/api/kits/{id}/export` | Export as SFZ zip |
| POST | `/api/kits/{id}/upload-drive` | Export and upload to Drive |

### Autopilot API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/autopilot/status` | Autopilot status + jobs + recent runs |
| POST | `/api/autopilot/start` | Start autopilot |
| POST | `/api/autopilot/stop` | Stop autopilot |
| POST | `/api/autopilot/jobs/{name}/run` | Run job immediately |
| POST | `/api/autopilot/jobs/{name}/toggle` | Enable/disable job |

### Kimi Bridge API
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/bridge/kimi` | Receive task from Kimi app |
| POST | `/api/bridge/omni` | Send work to Kimi app |
| GET | `/api/bridge/tasks` | Get pending Kimi tasks |
| POST | `/api/bridge/complete` | Mark Kimi task completed |

### Kimi Daily Pipeline API
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/kimi-daily/run` | Trigger daily extraction pipeline |
| GET | `/api/kimi-daily/history` | Recent extraction history |

### Vault API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/vault/search` | Search vault (q, category) |
| GET | `/api/vault/recent` | Recent vault entries |

### Audio Ingestion
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Receive audio metadata from ingestion watcher |
| POST | `/api/studio/analyze` | Analyze audio file metadata |

### Disk Cleaner
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cleaner/status` | Current disk usage |
| POST | `/api/cleaner/run` | Manual disk cleanup |

### Notifications
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications` | Recent notification history |

### Omi Webhook
| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook/omi` | Receive Omi ambient transcript |
| POST | `/process/kimi-daily` | Process today's Omi transcripts |

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health check |

---

## 11. Environment Variables Master List

| Variable | Required | Used By | Description |
|----------|----------|---------|-------------|
| `KIMI_API_KEY` | Yes (for swarm) | swarm.py, omni.py, omni_kimi_bridge.py | Kimi/Moonshot API key |
| `GOOGLE_API_KEY` | Yes (for Gemini) | swarm.py, music_library_aggregator.py | Google AI API key |
| `OPENROUTER_API_KEY` | Optional | swarm.py | OpenRouter API key |
| `XAI_API_KEY` | Optional | swarm.py | xAI (Grok) API key |
| `OLLAMA_BASE_URL` | No (default: localhost:11434/v1) | swarm.py | Ollama server URL |
| `GOOGLE_MODEL` | No (default: gemini-2.5-flash) | swarm.py, config.py | Gemini model name |
| `GEMINI_MODEL` | No (default: gemini-3.5-flash) | music_library_aggregator.py | Gemini model for extraction |
| `GOOGLE_OAUTH_JSON` | Optional | config.py | OAuth client configs (JSON blob) |
| `GOOGLE_OAUTH_OMNI_CLIENT_ID` | Optional | config.py | Google OAuth client ID |
| `GOOGLE_OAUTH_OMNI_CLIENT_SECRET` | Optional | config.py | Google OAuth client secret |
| `GOOGLE_OAUTH_OMNI_PROJECT_ID` | Optional | config.py | Google OAuth project ID |
| `SUNO_SESSION` | Optional | config.py | Suno music session cookie |
| `MAX_WORKERS` | No (default: 2) | config.py | Scheduler max workers |
| `RATE_LIMIT_DELAY` | No (default: 1.0) | config.py | Rate limit delay (seconds) |
| `OMNI_HOST` | No (default: 0.0.0.0) | config.py | Dashboard bind address |
| `OMNI_PORT` | No (default: 8500) | config.py | Dashboard port |
| `OMNI_DEBUG` | No (default: true) | config.py | Debug mode toggle |
| `SERPER_API_KEY` | Yes (for MLA) | music_library_aggregator.py | Serper.dev API key |
| `MLA_DRY_RUN` | No (default: 0) | music_library_aggregator.py | Dry run mode |
| `NOTIFY_EMAIL` | No (default: paperworkmg@gmail.com) | email_notifier.py | Notification recipient |
| `SMTP_HOST` | No (default: smtp.gmail.com) | email_notifier.py | SMTP server |
| `SMTP_PORT` | No (default: 587) | email_notifier.py | SMTP port |
| `SMTP_USER` | No (default: paperworkmg@gmail.com) | email_notifier.py | SMTP username |
| `SMTP_PASS` | Yes (for email) | email_notifier.py | SMTP app password |
| `EMAIL_USER` | Yes (for fetch/send) | fetch_emails.py, send_emails.py | Gmail address |
| `EMAIL_PASS` | Yes (for fetch/send) | fetch_emails.py, send_emails.py | Gmail app password |
| `SLACK_WEBHOOK_URL` | Optional | omni.py | Slack incoming webhook |
| `CRM_API_URL` | Optional | omni.py | External CRM API URL |

**Note:** Several scripts have hardcoded credentials (Gmail app passwords, SMB credentials). These should be migrated to environment variables.

---

## 12. File Map

### Shell Scripts (6 files)
```
/Users/mtb/Omni-Studio/master_loop.sh        # Cron master cycle
/Users/mtb/Omni-Studio/watchdog.sh           # Filesystem lead watchdog + pitch generator
/Users/mtb/Omni-Studio/status.sh             # Launchd service status checker
/Users/mtb/Omni-Studio/run_pipeline.sh       # One-shot pipeline runner
/Users/mtb/Omni-Studio/studio_core.sh        # Network discovery + AI analysis
/Users/mtb/Omni-Studio/verify_and_run.sh     # Pre-flight check + pipeline launcher
```

### Agents (5 files)
```
/Users/mtb/Omni-Studio/agents/ghost_followup.py              # Follow-up nudge engine
/Users/mtb/Omni-Studio/agents/inbound_agent.py               # Autonomous email responder
/Users/mtb/Omni-Studio/agents/instagram_coldlist.py           # Instagram cold DM generator
/Users/mtb/Omni-Studio/agents/music_library_aggregator.py    # LinkedIn A&R contact finder
/Users/mtb/Omni-Studio/agents/studio_agent.py                # Lead processor + pitch writer
```

### Dashboard (16 key files)
```
/Users/mtb/Omni-Studio/dashboard/app.py              # FastAPI routes (modular version)
/Users/mtb/Omni-Studio/dashboard/omni.py             # Monolithic FastAPI app (1252 lines)
/Users/mtb/Omni-Studio/dashboard/config.py           # Configuration (env-driven)
/Users/mtb/Omni-Studio/dashboard/database.py         # SQLite schema + CRUD
/Users/mtb/Omni-Studio/dashboard/scheduler.py        # APScheduler cron executor
/Users/mtb/Omni-Studio/dashboard/swarm.py            # Multi-agent orchestrator
/Users/mtb/Omni-Studio/dashboard/bridge.py           # Kimi <-> Omni bridge
/Users/mtb/Omni-Studio/dashboard/omi_kimi_bridge.py  # Omi ambient transcript bridge
/Users/mtb/Omni-Studio/dashboard/kimi_client.py      # Kimi CLI client
/Users/mtb/Omni-Studio/dashboard/sample_library.py   # Sample database + search
/Users/mtb/Omni-Studio/dashboard/sample_scanner.py   # Audio file scanner + analysis
/Users/mtb/Omni-Studio/dashboard/sampler_engine.py   # Kit builder + SFZ exporter
/Users/mtb/Omni-Studio/dashboard/daw_watcher.py      # Logic Pro export watcher
/Users/mtb/Omni-Studio/dashboard/email_notifier.py   # Email notification sender
/Users/mtb/Omni-Studio/dashboard/google_drive.py     # Google Drive uploader
/Users/mtb/Omni-Studio/dashboard/contacts.py         # CRM contacts module
/Users/mtb/Omni-Studio/dashboard/launcher.py         # App launcher (opens browser)
```

### Scripts (8 files)
```
/Users/mtb/Omni-Studio/scripts/alerts_watcher.py              # Google Alerts RSS reader
/Users/mtb/Omni-Studio/scripts/audit_missed_funds.py           # Historical payment auditor
/Users/mtb/Omni-Studio/scripts/dashboard.py                   # ASCII revenue dashboard
/Users/mtb/Omni-Studio/scripts/generate_national_contacts.py  # Media contact CSV generator
/Users/mtb/Omni-Studio/scripts/income_watchdog.py             # Payment detection + gate codes
/Users/mtb/Omni-Studio/scripts/press_pitch_generator.py       # PR pitch generator
/Users/mtb/Omni-Studio/scripts/send_batch.py                  # Manual Instagram DM sender
/Users/mtb/Omni-Studio/scripts/view_leads.py                  # CLI lead database viewer
```

### Core (6 files)
```
/Users/mtb/Omni-Studio/core/autopilot.py                      # Autonomous job scheduler
/Users/mtb/Omni-Studio/core/check_calendar.py                 # Booking conflict checker
/Users/mtb/Omni-Studio/core/cross_render.py                   # Text->music->stems->kit pipeline
/Users/mtb/Omni-Studio/core/invoice.py                        # Invoice generator
/Users/mtb/Omni-Studio/core/master_orchestrator.py            # Long-running cycle daemon
/Users/mtb/Omni-Studio/core/migrate_music_library_schema.py   # DB schema migration
```

### Integrations (7 files)
```
/Users/mtb/Omni-Studio/integrations/scraper.py              # Playwright web scraper
/Users/mtb/Omni-Studio/integrations/send_ar_pitches.py       # A&R email sender
/Users/mtb/Omni-Studio/integrations/send_emails.py           # Generic email queue flusher
/Users/mtb/Omni-Studio/integrations/send_press_pitches.py    # PR email sender
/Users/mtb/Omni-Studio/integrations/fetch_emails.py          # IMAP email fetcher
/Users/mtb/Omni-Studio/integrations/gmail_client.py          # Gmail OAuth2 client
/Users/mtb/Omni-Studio/integrations/__init__.py              # Package init
```

### Data/Vault (3 files)
```
/Users/mtb/Omni-Studio/data/vault/vault.py          # Full vault DAO (991 lines, FTS5, catalog)
/Users/mtb/Omni-Studio/data/vault/schema.sql         # Vault schema (383 lines)
/Users/mtb/Omni-Studio/data/vault/import_tracks.py   # Catalog track importer
```

### Superpowers (2 design docs)
```
/Users/mtb/Omni-Studio/superpowers/specs/2026-07-19-music-library-aggregator-design.md
/Users/mtb/Omni-Studio/superpowers/plans/2026-07-19-music-library-aggregator-plan.md
```

### GODMODE (AI development framework)
```
/Users/mtb/Omni-Studio/GODMODE/README.md           # Installation + usage guide
/Users/mtb/Omni-Studio/GODMODE/claude/CLAUDE.md     # Orchestrator rules
/Users/mtb/Omni-Studio/GODMODE/skills/              # 50+ skills across 11 categories
/Users/mtb/Omni-Studio/GODMODE/rules/delegator/     # GPT/Gemini delegation rules
```

### Config Files
```
/Users/mtb/Omni-Studio/.env.example     # Environment variable template
/Users/mtb/Omni-Studio/config/.env      # Live environment config (SENSITIVE)
/Users/mtb/Omni-Studio/config/credentials.json      # Google OAuth credentials
/Users/mtb/Omni-Studio/config/gmail_credentials.json # Gmail OAuth credentials
/Users/mtb/Omni-Studio/config/token.pickle           # Gmail OAuth token cache
/Users/mtb/Omni-Studio/dashboard/requirements.txt    # Python dependencies
```

---

## Notes for Dashboard Redesign

### Current State Observations
1. **Two competing app files:** `app.py` (modular, 396 lines) and `omni.py` (monolithic, 1252 lines). The monolith is the active one (launcher.py imports `omni:app`). The modular `app.py` is incomplete -- missing many API groups that omni.py has.
2. **No unified lead management UI** -- leads are managed via CLI scripts and filesystem conventions. A dashboard page for leads/pipeline would be high-value.
3. **No revenue/finance page** -- revenue data exists in pitch files and the ASCII dashboard but is not surfaced in the web UI.
4. **No DAW watcher status page** -- daw_watcher runs but has no dashboard exposure.
5. **No catalog analytics page** -- vault.db has rich catalog track data with HPI scores and verdicts but no UI.
6. **No contacts/CRM page** -- contacts.py exists but app.py doesn't expose it; omni.py doesn't use it.
7. **Plugins are hardcoded** -- Financial Data, Economic Calendar, Music Industry, Weather plugins return static data.
8. **Autopilot has full API** but the web UI template (dashboard.html) needs to be checked for actual exposure.

### High-Value New Dashboard Pages
1. **Lead Pipeline Board** -- Kanban-style view: Incoming -> Processing -> Pitched -> Contacted -> Confirmed
2. **Revenue Tracker** -- Pipeline value, confirmed payments, projected revenue, gate code status
3. **Catalog Analytics** -- HPI scores, verdict buckets, key distribution, BPM distribution, top prospects
4. **Agent Health Monitor** -- Real-time agent status, task history, swarm run visualization
5. **Omi/Kimi Daily Briefing** -- Today's extractions: music IP, CRM notes, SOPs with FTS5 search
6. **Sample Library Browser** -- Search/filter audio with key, tempo, type; waveform preview; kit builder
7. **DAW Export Feed** -- Real-time Logic Pro export detection with Drive upload status
8. **Contact CRM** -- Contact management with import, status tracking, outreach history
9. **Press/Media Dashboard** -- Media contact coverage, sent pitches, response tracking
10. **System Health** -- Autopilot jobs, disk usage, log tail, service status

