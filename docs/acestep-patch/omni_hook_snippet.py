# ── omni.py hook — ACE-Step routes ──────────────────────────────────────────
# In app/dashboard/omni.py, omni:app is the live hub (launcher.py runs it)
# and routes are registered as decorators on `app` (created ~line 817 in
# the 2026-10-21 snapshot:  app = FastAPI(title="Omni-Studio", ...)).
#
# Add these two lines AFTER the `app = FastAPI(...)` line. The guard keeps
# the whole studio booting even if the ACE-Step modules are absent —
# same graceful-skip behaviour as the other side services.
#
#     try:
#         from acestep_routes import register_acestep_routes
#         register_acestep_routes(app)
#     except Exception as e:
#         print(f"[acestep] routes not loaded: {e}")
#
# That's the entire omni.py change. Everything else lives in the new
# modules: acestep_config.py, acestep_client.py, comfyui_client.py,
# acestep_routes.py.
# ────────────────────────────────────────────────────────────────────────────
