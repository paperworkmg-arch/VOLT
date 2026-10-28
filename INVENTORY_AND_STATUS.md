# Omni Studio — Full Source Intake, 2026-10-23

Intake: 52 files across two uploads (Pinokio/JS layer + Python dashboard layer)
plus the Volt bolt icon (1024x1024 PNG, now `icon.png` at repo root — pinokio.json
and pinokio.js both expect exactly that filename).

## Verified by actually running it (2026-10-23, this workspace)
- All 22 Python files pass syntax check; all 15 JS files pass `node --check`;
  all 4 JSON files parse.
- NO hardcoded secrets in any Omni file. Every API key is read from the
  environment / `.env` (config.py: 16 env lookups). `.env.example` included —
  fill it on the Mac, never commit a filled one.
- BOOT TEST PASSED: in a clean venv with requirements.txt installed,
  `python omni.py` started on http://127.0.0.1:8500 and answered:
  - GET /api/health -> 200 {"status":"ok","agents":6,"tasks":5}
  - GET /api/catalog/summary -> 200 (via the vault shim below)
  - GET /api/catalog/tracks -> 200 []
  - GET / -> 404 (expected: no frontend dist / templates in the uploads — see gaps)

## The one blocker that was hiding in the code
omni.py line 35 imports `from vault import Vault` UNGUARDED from
`app/dashboard/data/vault/vault.py`, then calls init_schema() at startup.
That file was NOT in the uploads — without it the dashboard crashes instantly.
FIX INCLUDED: `app/dashboard/data/vault/vault.py` in this package is a clean
SQLite shim written 2026-10-23 implementing exactly the 8 methods omni.py
calls (init_schema, get_catalog_tracks, get_track, get_catalog_summary,
get_top_prospects, get_catalog_by_key, get_catalog_by_bucket, search_catalog).
If the original vault.py is still on the Mac, swap it in — routes won't notice.

## Still missing (not in either upload)
1. app/volt-dashboard/ — React frontend source + built dist/. omni.py serves
   it if present; without it the API runs but / is 404. Also templates/ and
   static/ contents for the Jinja fallback UI (empty placeholder dirs included
   because omni.py mounts /static unconditionally and would crash without one).
2. app/dashboard/app_experimental.py (uploaded as app-2.py) imports `plugins`
   and `core.autopilot` / `core.cross_render` — none uploaded. It's the
   experimental app, NOT the main server; omni.py does not need it.
3. Audio submodules referenced by Pinokio start.js: app/stabledaw/,
   app/stable-audio-3/, app/tascar/ (+ ACE-Step) — pulled from their own
   GitHub repos per README, not part of this source drop.
4. Optional, degraded-not-fatal (imports are inside try/except):
   agents/music_library_aggregator.py, scripts/audit_missed_funds.py.
5. sota_lora_training.py needs heavy ML deps (audioldm2, stable_audio_tools,
   torchaudio, transformers, bitsandbytes) — not in requirements.txt; treat
   as a separate training rig, GPU/Mac-Studio class work.

## Layout notes
- Uploads arrive flat; this package restores the README layout:
  repo root (Pinokio) / app/dashboard (Python) / app/volt-dashboard / mac/
  (launchers, Info.plist, launchd plist, setup-macbook-air.sh, build.sh).
- omni.py is the real server: 2,175 lines, 92 routes, PORT 8500, single file
  with its own DB/agents/swarm/scheduler logic. database.py/swarm.py/
  scheduler.py/config.py are the modular set used by app_experimental.py.
- Two GitHub homes are referenced: paperworkmg-arch/omni-studio
  (package.json, setup script) vs VoltRecords/omni-studio (pinokio.json link).
  Pick one as canonical before the next push.

## Next step to run it on the Mac
1. Copy this folder to ~/pinokio/api/omni-studio (or unzip into Pinokio).
2. cp .env.example app/.env and fill the keys you actually use.
   (Correction 2026-10-23: an earlier draft said repo root — wrong. omni.py
   loads BASE.parent/.env and config.py loads PROJECT/.env; both are app/.env.
   Verified in the Pinokio-location rehearsal below.)
3. Pinokio -> Omni Studio -> Install -> Start, or manually:
   cd app/dashboard && pip install -r requirements.txt && python3 omni.py
4. Open http://127.0.0.1:8500/api/health to confirm, then restore the
   volt-dashboard dist (or templates) for the UI root.

## Rehearsal run 2026-10-23 (Pinokio location, this workspace)
Steps 1-4 executed verbatim against a staging copy at ~/pinokio/api/omni-studio:
folder copied, app/.env created from the example, venv built from
requirements.txt (all deps import), `python omni.py` booted and
GET /api/health -> 200 {"status":"ok","agents":6,"tasks":5},
GET /api/agents -> 200 (Atlas/Scout/...), GET / -> 404 as expected pre-frontend.
Note install.js (Pinokio's Install button) additionally clones
stable-audio-3 / stabledaw / tascar itself and runs npm builds in
app/volt-dashboard — those builds fail until the frontend source is restored,
but the dashboard venv step succeeds independently, and the manual path above
does not need them.

## WanGP integration (added 2026-10-23, at Mykel's request)
WanGP (Wan2GP by DeepBeepMeep — generative video/image/audio/TTS:
Wan 2.1/2.2, LTX-2, Hunyuan Video, Flux, Qwen Image, Ace Step; Gradio UI,
port 7860; MCP server built in) is integrated as a first-class Omni app:
- install.js clones https://github.com/deepbeepmeep/Wan2GP.git into
  app/wangp on Install (same pattern as the other apps — the WanGP source
  itself is NOT bundled in this zip).
- wangp.js (repo root) is the Pinokio launcher: own venv at app/wangp/env,
  runs `python wgp.py --server-name 127.0.0.1 --server-port 7860
  --open-browser` (flags verified against shared/cli_args.py in the source).
- Pinokio sidebar has a WanGP menu entry; omni.py's AUDIO_APPS registry has
  a "wangp" entry (port 7860), verified live: GET /api/audio-apps lists it.
- Staging install holds the full clone (3,141 files, 117 MB, wgp.py
  syntax-checked). WanGP's heavy environment (PyTorch/CUDA) is created by
  ITS OWN installer (app/wangp/scripts/install.sh) on the target machine —
  generation requires a GPU; this staging VM has none, so the env was not
  built here and no generation was test-run.

## Recovered from the canonical repo (2026-10-23→25, at Mykel's "go all")
The two pieces missing from the original uploads were found in the public
repo paperworkmg-arch/VOLT (the repo paperworkmg-arch/omni-studio redirects
to; VoltRecords/omni-studio does not exist publicly) and restored:
- app/volt-dashboard: full React source (src/, vite config) + a freshly
  built dist/ (2,292 modules, 2.1 MB). Dashboard UI root now serves 200
  (was 404); the Pinokio frontend-build step no longer blocks install.
- app/dashboard/data/vault/: the REAL vault.py (all 8 methods omni.py
  calls, plus schema.sql it requires — copy the whole folder, not just
  vault.py) replaces the SQLite shim (shim kept at hidden_files/
  vault_shim_backup.py). /api/catalog/summary now answers from the real
  Vault schema.
- Canonical repo = paperworkmg-arch/VOLT. Nothing has been pushed back to
  it yet (needs Mykel's GitHub auth); this package is the push-ready set.

## TASCAR built (2026-10-27, staging)
Full build from the app/tascar clone: install.js Linux deps minus
libwebkit2gtk-4.0-dev (not on Ubuntu noble) + libcunit1-dev +
libxerces-c-dev + xxd; stale partial *_glade.h files cleared and
regenerated. Outputs: gui/build/tascar, libtascar.so.0.239.3, 163 plugin
.so files, apps/build/tascar_cli (help verified). Build outputs are NOT
bundled in this zip — rebuild on the target with `make -j$(nproc)` after
installing the deps above. Registry shows tascar "stopped" because it has
no web port (CLI renderer, not a server).
