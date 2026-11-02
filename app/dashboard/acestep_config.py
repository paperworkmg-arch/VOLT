"""ACE-Step song generation settings — VOLT / Omni-Studio dashboard.

Follows the same pattern as config.py: every value comes from the
environment (app/.env) with a low-memory default sized for the MacBook Air.
Nothing here is hard-coded to a machine; paths resolve off config.BASE.

Low-memory recipe (ACE-Step 1.5 plan, 2026-11-02):
  - Song model: Turbo (2B), 8 steps, guidance off  -> daily driver
  - Planner:    0.6B, offloaded to system RAM      -> step up only after test
  - Backend:    PyTorch path (already set in the staged launcher)
  - Batch:      1 at a time
"""
import os
from pathlib import Path

import config

# === Master switch (proof step 3 runs behind this) ===
ACESTEP_ENABLED = os.getenv("ACESTEP_ENABLED", "1").lower() in ("1", "true", "yes")

# The launcher backend is JWT-guarded; the hub sets up a local user and
# caches its token (see acestep_client). Any name works — it is a local,
# single-user backend — but keep it stable so repeat setups reuse it.
ACESTEP_USERNAME = os.getenv("ACESTEP_USERNAME", "volt-hub")

# === Surfaces ===
# Primary: the staged launcher's backend (ace-step-ui.pinokio).
# It wraps the engine and exposes the simple job flow: start -> poll -> file.
# VERIFY the three paths in acestep_client.CONTRACT against the launcher's
# README during proof step 1; if they differ, only CONTRACT changes.
ACESTEP_API_BASE = os.getenv("ACESTEP_API_BASE", "http://127.0.0.1:3001")
# The engine's own API (the launcher runs it with the API enabled).
# Kept for health checks / future direct route; not the primary path.
ACESTEP_ENGINE_BASE = os.getenv("ACESTEP_ENGINE_BASE", "http://127.0.0.1:8001")
# Second surface: ComfyUI native ACE-Step (picture work, batch auditions).
COMFYUI_BASE = os.getenv("COMFYUI_BASE", "http://127.0.0.1:8188")

# === Generation defaults (Turbo low-memory tier) ===
ACESTEP_MODEL = os.getenv("ACESTEP_MODEL", "turbo")            # turbo | base | xl (xl needs 12GB+)
ACESTEP_PLANNER = os.getenv("ACESTEP_PLANNER", "0.6b")         # 0.6b | 1.7b | none
ACESTEP_DEFAULT_DURATION = int(os.getenv("ACESTEP_DEFAULT_DURATION", "60"))   # seconds
ACESTEP_MAX_DURATION = int(os.getenv("ACESTEP_MAX_DURATION", "240"))          # Air guardrail
ACESTEP_DEFAULT_FORMAT = os.getenv("ACESTEP_DEFAULT_FORMAT", "flac")          # flac masters, mp3 shares
ACESTEP_STEPS = int(os.getenv("ACESTEP_STEPS", "8"))           # Turbo recipe: 8 steps
ACESTEP_GUIDANCE = float(os.getenv("ACESTEP_GUIDANCE", "1.0"))  # Turbo recipe: guidance off

# === Job handling ===
ACESTEP_POLL_SECONDS = float(os.getenv("ACESTEP_POLL_SECONDS", "2.0"))
ACESTEP_JOB_TIMEOUT = int(os.getenv("ACESTEP_JOB_TIMEOUT", "900"))  # 15 min ceiling on the Air

# The hub's own port (for the best-effort /ingest call in acestep_routes).
HUB_PORT = config.PORT

# === Catalog write-back ===
# Finished songs land here as DRAFTS with a provenance sidecar, then enter
# the normal approval flow. They never skip the ownership/clearance check.
ACESTEP_INBOX_DIR = Path(os.getenv("ACESTEP_INBOX_DIR", str(config.DATA_DIR / "acestep_inbox")))
