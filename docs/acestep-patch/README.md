> **Pushed layout (branch `acestep-wiring`):** the code files from the table below were pushed to their real homes in the repo (dashboard modules, root starter, front-end panel, comfyui/). This README and the paste-in snippets (omni hook, app entry, env block) live together here in `docs/acestep-patch/` so nothing in the repo was overwritten.

# VOLT — ACE-Step 1.5 wiring patch set

Connects the already-staged ACE-Step 1.5 launcher to the live Omni-Studio
hub, per the 2026-11-02 plan. ACE-Step takes the full-song lane; Stable
Audio keeps its lane; Suno stays the rented benchmark until the proof
below passes.

Built against `paperworkmg-arch/VOLT` as read on 2026-11-02 (hub =
`app/dashboard/omni.py`, FastAPI, port 8500; starter = root Pinokio
scripts; front end = `app/volt-dashboard`). Patterns were matched to the
project's own code (config.py env style, omni.py decorator routes,
`database.log_activity`, the `/ingest` front door).

## File map — every patch file has exactly one home

| Patch file | Drop into repo at | What it does |
|---|---|---|
| `app/dashboard/acestep_config.py` | same path | All ACE-Step settings, env-driven, Air-sized defaults |
| `app/dashboard/acestep_client.py` | same path | Engine client: submit → poll → download |
| `app/dashboard/comfyui_client.py` | same path | ComfyUI client + the workflow builder |
| `app/dashboard/acestep_routes.py` | same path | `/api/acestep/*` routes + catalog draft filing |
| `app/dashboard/omni_hook_snippet.py` | read it, then delete | The only omni.py change: 2 lines after `app = FastAPI(...)` |
| `start_acestep.js` | repo root | Starter block; skips gracefully if the launcher is absent |
| `app/volt-dashboard/acestep_app_entry.ts` | read it, paste the object | ACE-Step entry for the audio-apps list in `use-audio-apps.ts` |
| `app/volt-dashboard/GeneratePanel.tsx` | `app/volt-dashboard/src/components/` | Generate panel (prompt/lyrics/length/BPM/key, engine or ComfyUI) |
| `comfyui/acestep_text2song_lowmem.json` | keep with the project | The same graph in ComfyUI API format, for hand runs |
| `env_acestep.example` | append to `app/.env` | Every setting, with defaults |

In `start.js`, add one step after the Stable Audio daemon block:

```js
{ method: "script.start", params: { uri: "start_acestep.js" } },
```

## Verify at drop-in (four small things, all marked in the code)

1. **Launcher contract — confirmed 2026-11-02** from the launcher's own
   README + start.js (read on the Mac): JWT setup at
   `POST /api/auth/setup`, `POST /api/generate` → `{jobId}`,
   `GET /api/generate/status/{jobId}`, no download endpoint (audio is
   referenced by the status payload). The client already speaks exactly
   this. Two small things remain for proof step 2, against the *running*
   backend: the status payload's exact audio-reference key (the client
   searches the common ones) and whether the optional fields
   (duration/bpm/key) are honoured or ignored.
2. **Checkpoint name** — `comfyui_client.CHECKPOINT` and node 1 of the
   workflow JSON must match the all-in-one Turbo checkpoint file actually
   in ComfyUI's `models/checkpoints`.
3. **omni.py drift** — the hook targets the `app = FastAPI(...)` line
   (~line 817 in the Oct 21 snapshot; the repo moved on Oct 28). The
   guarded try/except means a miss costs nothing — the studio boots and
   the health endpoint simply won't exist until the lines land.
4. **Front-end field names** — the app-entry object mirrors the described
   list shape; match the sibling entries (StableDAW etc.) if a key name
   differs. Also run the dashboard build once after adding the panel.

The routes also make a best-effort POST to the hub's own `/ingest`
(filename + archive_path, the fields its handler reads today). Filing
never depends on it: the audio + provenance sidecar land in the inbox
either way, and the ingest result is written into the sidecar.

## Prove it in three steps (the plan's order — don't skip)

1. **Engine alone.** Install through the staged launcher; generate one
   30s instrumental and one 60s vocal song on Turbo + 0.6B. Note time
   and clean finish. Confirm the CONTRACT paths against the real backend.
2. **Engine over its API.** One manual round trip through the client:
   submit → poll → FLAC lands in the inbox with its sidecar.
3. **One thin slice through VOLT.** With `ACESTEP_ENABLED=1`, generate
   from the front-end panel; the song should appear as a catalog draft
   in the approval flow. Only then widen the panel or the planner.

## Defaults (low-memory recipe, sized to the MacBook Air)

Turbo model · 8 steps · guidance 1.0 (off) · planner 0.6B offloaded ·
batch 1 · FLAC from the engine, MP3 from ComfyUI · default length 60s,
hard cap 240s (`ACESTEP_MAX_DURATION`) · jobs time out at 15 min.

## House rules baked in

- Every generated track is filed as a **draft** with full provenance
  (surface, model, planner, prompt, lyrics, seed, params) and passes the
  normal ownership/clearance check before any sync pitch.
- `ACESTEP_ENABLED=0` closes the generate endpoints without touching
  anything else.
- No secrets in code: every value resolves from `app/.env`.
