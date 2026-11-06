# Omni Studio — Base44 Dev Environment

## Architecture
- **Frontend**: React + Vite SPA at `app/volt-dashboard/` (port 3000). Proxies `/api`, `/webhook`, `/process` to the backend via `OMNI_API_TARGET` env var (defaults to `http://127.0.0.1:8500`).
- **Backend**: FastAPI single-file app at `app/dashboard/omni.py` (port 8500). Uses SQLite (no external DB needed). All data stored in `app/dashboard/data/`.

## Running
```bash
docker compose -f docker-compose.base44.yml up -d --build
```
Frontend health: `http://localhost:3000` | Backend health: `http://localhost:8500/api/health`

## Key Details
- Backend binds `0.0.0.0:8500` via uvicorn CLI args (code hardcodes `127.0.0.1` but CLI overrides).
- Vite proxy target is configurable via `OMNI_API_TARGET` env var (set to `http://backend:8500` in compose).
- `librosa`, `numpy`, `mutagen` are in requirements but imported lazily — app boots without system audio libs.
- LLM provider keys (KIMI_API_KEY, OPENROUTER_API_KEY, GOOGLE_API_KEY, XAI_API_KEY) are optional; the dashboard renders without them but AI agent/chat features won't work.
- `templates/` dir is created at startup but not used (frontend is a React SPA).
- Catalog data comes from `app/dashboard/data/vault/vault.db` (SQLite, schema auto-initialized).

## Verification
- `curl http://localhost:8500/api/health` → `{"status":"ok",...}`
- `curl http://localhost:8500/api/catalog/summary` → catalog stats
- Frontend at `http://localhost:3000` shows the Volt Records catalog console.
