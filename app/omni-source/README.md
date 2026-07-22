# Omni-Studio

An enterprise-grade, local-first command center for AI agents, scheduled tasks, sample libraries, and DAW-ready sampler kits.

## What It Does

Omni-Studio is a FastAPI dashboard that runs entirely on your machine. It gives you:

- **Agent Swarm** — Decompose objectives and dispatch parallel AI agents (Atlas, Scout, Forge, Pulse, Echo).
- **Task Scheduler** — Cron-like scheduled tasks that call LLMs and log results.
- **Sample Library** — Scan local audio, extract key/tempo, search/filter, and sync to Google Drive.
- **Universal Sampler** — Build drum or chromatic kits and export them as **SFZ** (works in any DAW) or upload to Drive.
- **Sites** — Spin up simple micro-sites from templates.
- **Chat** — Direct LLM chat with multiple providers.
- **Plugins** — Built-in data plugins (financial, economic, music industry, weather).

## Quick Start

```bash
cd Omni-Studio/dashboard
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt

# Optional: copy env template and fill in your API keys
cp ../.env.example ../.env

python app.py
```

Open `http://localhost:8500`.

## Configuration

Create `Omni-Studio/.env`:

```env
# LLM providers (at least one recommended)
KIMI_API_KEY=your_kimi_key
GOOGLE_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
XAI_API_KEY=your_xai_key

# Google OAuth (do NOT hardcode these)
GOOGLE_OAUTH_OMNI_CLIENT_ID=...
GOOGLE_OAUTH_OMNI_CLIENT_SECRET=...
GOOGLE_OAUTH_OMNI_PROJECT_ID=...

# Google Drive service account for uploads
# Copy your service-account.json to dashboard/data/service-account.json

# Server
OMNI_HOST=0.0.0.0
OMNI_PORT=8500
OMNI_DEBUG=true
```

> ⚠️ **Security:** OAuth client secrets and API keys must live in `.env`. Hardcoded secrets have been removed from the codebase.

## Remote Access

The dashboard binds to `0.0.0.0` by default, so it is reachable from any device on your local network:

```bash
# Find your local IP
ipconfig getifaddr en0   # macOS
# Then open http://YOUR_IP:8500 on another device
```

For production / internet access, put it behind a reverse proxy (nginx, Caddy, or Tailscale) and enable HTTPS. Do **not** expose `DEBUG=true` to the internet.

### Example: Caddy reverse proxy

```Caddyfile
omni.yourdomain.com {
    reverse_proxy localhost:8500
}
```

### Example: systemd service

```ini
[Unit]
Description=Omni-Studio Dashboard
After=network.target

[Service]
Type=simple
User=omni
WorkingDirectory=/path/to/Omni-Studio/dashboard
ExecStart=/path/to/Omni-Studio/.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8500
Restart=always
Environment=OMNI_DEBUG=false

[Install]
WantedBy=multi-user.target
```

## Sampler System

Build kits from local sounds and use them in any DAW:

1. Go to the **♫ Samples** tab and click **Scan** to discover local audio.
2. Click **Analyze** to detect key and tempo.
3. Click **+** next to samples you want in a kit.
4. Switch to the **🎹 Sampler** tab, name your kit, choose **Drum Kit** or **Chromatic**, and click **Create Kit**.
5. Click **📦 Export SFZ** to download a zip containing `.sfz` + samples.
6. Load the `.sfz` in any sampler (SFZ Player, Kontakt, Decent Sampler, Logic Sampler, etc.).

You can also upload kits directly to Google Drive.

## Running Tests

```bash
cd Omni-Studio/dashboard
source ../.venv/bin/activate
pytest tests/ -v
```

## Project Layout

```
Omni-Studio/
├── dashboard/           # FastAPI app + UI
│   ├── app.py           # Main application routes
│   ├── config.py        # Configuration (env-driven)
│   ├── database.py      # Dashboard SQLite schema
│   ├── scheduler.py     # Cron task scheduler
│   ├── swarm.py         # Multi-agent orchestration
│   ├── plugins/         # Plugin loader + built-ins
│   ├── sample_library.py
│   ├── sample_scanner.py
│   ├── sampler_engine.py
│   ├── google_drive.py
│   ├── templates/
│   ├── static/
│   └── tests/
├── agents/              # Standalone agent scripts
├── core/                # Orchestrator modules
├── omni_studio_data/    # Data pipelines
└── stemdeck/            # Stem separation (separate project)
```

## Security Checklist

- [ ] API keys and OAuth secrets are in `.env`, never committed.
- [ ] `dashboard/data/service-account.json` is not committed.
- [ ] `OMNI_DEBUG=false` for remote/internet deployments.
- [ ] Use HTTPS and basic auth or VPN for external access.

## License

MIT — use at your own risk.
