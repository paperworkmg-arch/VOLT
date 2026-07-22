"""Dashboard configuration — wires into Omni-Studio's real data."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).parent
PROJECT = BASE.parent
load_dotenv(PROJECT / ".env")

# === Paths ===
DATA_DIR = BASE / "data"
SITES_DIR = BASE / "sites"
PLUGINS_DIR = BASE / "plugins"
DB_PATH = DATA_DIR / "dashboard.db"

# === LLM Providers ===
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = "https://api.kimi.com/coding"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# === Google OAuth (DO NOT hardcode secrets) ===
# Set either per-project env vars or a single JSON blob in GOOGLE_OAUTH_JSON.
# Example .env:
#   GOOGLE_OAUTH_OMNI_CLIENT_ID=...
#   GOOGLE_OAUTH_OMNI_CLIENT_SECRET=...
#   GOOGLE_OAUTH_OMNI_PROJECT_ID=...
def _load_google_oauth() -> dict:
    """Load OAuth clients from env vars; never commit secrets."""
    raw_json = os.getenv("GOOGLE_OAUTH_JSON", "")
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            pass
    clients = {}
    for key in ("omni", "soundwave"):
        prefix = f"GOOGLE_OAUTH_{key.upper()}_"
        cid = os.getenv(f"{prefix}CLIENT_ID", "")
        csec = os.getenv(f"{prefix}CLIENT_SECRET", "")
        pid = os.getenv(f"{prefix}PROJECT_ID", "")
        if cid and csec:
            clients[key] = {"client_id": cid, "client_secret": csec, "project_id": pid}
    return clients


GOOGLE_OAUTH = _load_google_oauth()

# === Suno Music ===
SUNO_SESSION = os.getenv("SUNO_SESSION", "")

# === Scheduler ===
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))

# === Dashboard Server ===
# Bind to 0.0.0.0 so the dashboard is reachable remotely on your LAN.
# Use OMNI_HOST/OMNI_PORT env vars to override without editing code.
HOST = os.getenv("OMNI_HOST", "0.0.0.0")
PORT = int(os.getenv("OMNI_PORT", "8500"))
DEBUG = os.getenv("OMNI_DEBUG", "true").lower() in ("1", "true", "yes")
