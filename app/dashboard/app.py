"""Omni-Studio Experimental Features Dashboard — FastAPI main app."""
import json
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

# Repo root on path so `core.*` (autopilot, cross_render) resolves when run from dashboard/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import BASE, HOST, PORT, DEBUG
from database import (
    init_db, get_tasks, get_agents, get_plugins, get_sites,
    get_swarm_runs, get_activity, get_task_results,
    update_task_status, update_agent_status, add_task_result, log_activity
)
from swarm import swarm, call_llm
from scheduler import scheduler, start_scheduler, sync_scheduled_tasks, execute_task
from plugins import plugin_manager, BUILTIN_PLUGINS, init_builtin_plugins
from sample_library import (
    init_sample_db, get_sample_stats, get_all_keys, search_samples,
    start_scan, complete_scan, get_scan_history, get_unanalyzed_samples,
    bulk_upsert_samples, get_sample
)
from sample_scanner import quick_scan, analyze_audio_metadata
from google_drive import upload_to_drive
from sampler_engine import create_kit, get_kits, get_kit, delete_kit, export_kit, update_kit_drive_url
from core.autopilot import autopilot, get_jobs, get_recent_runs, update_job
from core.cross_render import create_render, list_renders, get_render, run_render
from contacts import (
    list_contacts, get_contact, create_contact, update_contact, delete_contact, import_csv
)

# Volt Records catalog vault
VAULT_DIR = BASE.parent / "data" / "vault"
sys.path.insert(0, str(VAULT_DIR))
from vault import Vault

vault = Vault(str(VAULT_DIR / "vault.db"))
vault.init_schema()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    await init_db()
    await init_sample_db()
    await init_builtin_plugins()
    start_scheduler()
    await sync_scheduled_tasks()
    autopilot.start()
    await log_activity("system", "Dashboard + Autopilot started", "info")
    yield
    autopilot.stop()
    scheduler.shutdown()
    await log_activity("system", "Dashboard + Autopilot stopped", "info")


app = FastAPI(
    title="Omni-Studio Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Legacy static files (keep for compatibility)
app.mount("/legacy-static", StaticFiles(directory=str(BASE / "static")), name="legacy-static")

# Volt Dashboard SPA (built React app)
VOLT_DASHBOARD_DIST = BASE.parent / "volt-dashboard" / "dist"
if VOLT_DASHBOARD_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(VOLT_DASHBOARD_DIST / "assets")), name="volt-assets")


# === Main UI: Volt Records Catalog Dashboard ===

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the Volt Records catalog intelligence dashboard."""
    index_path = VOLT_DASHBOARD_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Fallback to legacy dashboard if build missing
    tasks = await get_tasks()
    agents = await get_agents()
    plugins = await get_plugins()
    activity = await get_activity(20)
    templates = Jinja2Templates(directory=str(BASE / "templates"))
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "tasks": tasks,
        "agents": agents,
        "plugins": plugins,
        "activity": activity,
        "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(str(VOLT_DASHBOARD_DIST / "favicon.ico")) if (VOLT_DASHBOARD_DIST / "favicon.ico").exists() else RedirectResponse(url="/legacy-static/favicon.ico")


# === Task API ===

@app.get("/api/tasks")
async def api_tasks():
    return await get_tasks()

@app.post("/api/tasks")
async def api_create_task(name: str = Form(...), type: str = Form("manual"), agent: str = Form("atlas"), cron: str = Form("")):
    db = await __import__("database", fromlist=["get_db"]).get_db()
    await db.execute(
        "INSERT INTO tasks (name, type, agent, scheduled_cron) VALUES (?, ?, ?, ?)",
        (name, type, agent, cron)
    )
    await db.commit()
    await db.close()
    if cron:
        await sync_scheduled_tasks()
    await log_activity("tasks", f"Created task: {name}")
    return RedirectResponse("/", status_code=303)

@app.post("/api/tasks/{task_id}/run")
async def api_run_task(task_id: int):
    task = await get_task_results(task_id)
    tasks = await get_tasks()
    task_info = next((t for t in tasks if t["id"] == task_id), None)
    if not task_info:
        raise HTTPException(404, "Task not found")
    asyncio.create_task(execute_task(task_id, task_info["name"], task_info.get("agent", "atlas")))
    return {"status": "started", "task_id": task_id}

@app.post("/api/tasks/{task_id}/toggle")
async def api_toggle_task(task_id: int):
    db = await __import__("database", fromlist=["get_db"]).get_db()
    await db.execute("UPDATE tasks SET enabled = NOT enabled WHERE id=?", (task_id,))
    await db.commit()
    await db.close()
    return {"status": "toggled"}


# === Agent API ===

@app.get("/api/agents")
async def api_agents():
    return await get_agents()

@app.post("/api/agents/{agent_id}/status")
async def api_agent_status(agent_id: int, status: str = Form(...)):
    await update_agent_status(agent_id, status)
    return {"status": "updated"}


# === Swarm API ===

@app.get("/api/swarm/runs")
async def api_swarm_runs():
    return await get_swarm_runs()

@app.post("/api/swarm/run")
async def api_swarm_run(objective: str = Form(...)):
    result = await swarm.run(objective)
    return result

@app.get("/api/swarm/status")
async def api_swarm_status():
    return {"running": swarm.running}


# === Plugin API ===

@app.get("/api/plugins")
async def api_plugins():
    return await get_plugins()

@app.post("/api/plugins/{name}/run")
async def api_run_plugin(name: str, **kwargs):
    return await plugin_manager.run_plugin(name)

@app.get("/api/plugins/registered")
async def api_registered_plugins():
    return plugin_manager.get_registered()


# === Activity API ===

@app.get("/api/activity")
async def api_activity(limit: int = 50):
    return await get_activity(limit)


# === Chat API (direct LLM call) ===

@app.post("/api/chat")
async def api_chat(message: str = Form(...), provider: str = Form("kimi"), model: str = Form("k2p7")):
    result = await call_llm(provider, model, [{"role": "user", "content": message}])
    return {"response": result}


# === Sites API ===

@app.get("/api/sites")
async def api_sites():
    return await get_sites()

@app.post("/api/sites")
async def api_create_site(name: str = Form(...), template: str = Form("default")):
    db = await __import__("database", fromlist=["get_db"]).get_db()
    site_dir = BASE / "sites" / name.lower().replace(" ", "-")
    site_dir.mkdir(parents=True, exist_ok=True)

    # Create basic site files
    (site_dir / "index.html").write_text(f"""<!DOCTYPE html>
<html><head><title>{name}</title><link rel="stylesheet" href="/legacy-static/css/site.css"></head>
<body><h1>{name}</h1><p>Powered by Omni-Studio</p></body></html>""")

    db_path = str(site_dir / "site.db")
    await db.execute(
        "INSERT INTO sites (name, template, db_path, config) VALUES (?, ?, ?, ?)",
        (name, template, db_path, json.dumps({"dir": str(site_dir)}))
    )
    await db.commit()
    await db.close()
    await log_activity("sites", f"Site created: {name}")
    return RedirectResponse("/", status_code=303)


# === Sample Library API ===

@app.get("/api/samples/stats")
async def api_sample_stats():
    return await get_sample_stats()

@app.get("/api/samples/keys")
async def api_sample_keys():
    return await get_all_keys()

@app.get("/api/samples")
async def api_samples(
    q: str = "",
    key: str = "",
    tempo_min: float = 0,
    tempo_max: float = 999,
    sample_type: str = "",
    limit: int = 50,
    offset: int = 0,
):
    return await search_samples(
        q=q, key=key, tempo_min=tempo_min, tempo_max=tempo_max,
        sample_type=sample_type, limit=limit, offset=offset
    )

@app.post("/api/samples/scan")
async def api_scan_samples():
    scan_id = await start_scan()

    async def _scan():
        start_time = datetime.now()
        try:
            files = await quick_scan()
            await bulk_upsert_samples(files)
            duration = (datetime.now() - start_time).total_seconds()
            await complete_scan(scan_id, len(files), 0, duration)
            await log_activity("samples", f"Scan #{scan_id} complete: {len(files)} files")
        except Exception as exc:
            await complete_scan(scan_id, 0, 0, 0.0)
            await log_activity("samples", f"Scan #{scan_id} failed: {exc}", "error")

    asyncio.create_task(_scan())
    return {"status": "started", "scan_id": scan_id}

@app.get("/api/samples/scan-history")
async def api_scan_history():
    return await get_scan_history()

@app.post("/api/samples/analyze")
async def api_analyze_samples():
    samples = await get_unanalyzed_samples(limit=1000)
    if not samples:
        return {"status": "nothing_to_analyze"}

    async def _analyze():
        try:
            analyzed = await analyze_audio_metadata(samples)
            await bulk_upsert_samples(analyzed)
            await log_activity("samples", f"Analysis complete: {len(analyzed)} samples")
        except Exception as exc:
            await log_activity("samples", f"Analysis failed: {exc}", "error")

    asyncio.create_task(_analyze())
    return {"status": "started", "count": len(samples)}

@app.post("/api/samples/export")
async def api_export_sample(sample_id: int = Form(...)):
    sample = await get_sample(sample_id)
    if not sample:
        raise HTTPException(404, "Sample not found")
    try:
        result = await upload_to_drive(Path(sample["path"]))
        await log_activity("samples", f"Exported to Drive: {sample['filename']}")
        return {"status": "uploaded", "url": result["url"], "id": result["id"]}
    except FileNotFoundError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# === Sampler / Kit API ===

@app.get("/api/kits")
async def api_kits():
    return await get_kits()

@app.post("/api/kits")
async def api_create_kit(
    name: str = Form(...),
    description: str = Form(""),
    layout_type: str = Form("drum"),
    sample_ids: str = Form(...),
):
    ids = [int(x.strip()) for x in sample_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(400, "No valid sample IDs provided")
    kit_id = await create_kit(name, description, layout_type, ids)
    await log_activity("sampler", f"Created kit '{name}' with {len(ids)} samples")
    return {"status": "created", "kit_id": kit_id}

@app.get("/api/kits/{kit_id}")
async def api_get_kit(kit_id: int):
    kit = await get_kit(kit_id)
    if not kit:
        raise HTTPException(404, "Kit not found")
    return kit

@app.delete("/api/kits/{kit_id}")
async def api_delete_kit(kit_id: int):
    await delete_kit(kit_id)
    await log_activity("sampler", f"Deleted kit {kit_id}")
    return {"status": "deleted"}

@app.post("/api/kits/{kit_id}/export")
async def api_export_kit(kit_id: int, fmt: str = Form("sfz")):
    try:
        result = await export_kit(kit_id, fmt)
        await log_activity("sampler", f"Exported kit {kit_id} as {fmt}")
        return result
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

@app.post("/api/kits/{kit_id}/upload-drive")
async def api_upload_kit_drive(kit_id: int):
    try:
        result = await export_kit(kit_id, "sfz")
        zip_path = Path(result["zip"])
        drive_result = await upload_to_drive(zip_path, folder_name="OMNI Sampler Kits")
        await update_kit_drive_url(kit_id, drive_result["url"])
        await log_activity("sampler", f"Uploaded kit {kit_id} to Drive")
        return {"status": "uploaded", "url": drive_result["url"], "zip": str(zip_path)}
    except FileNotFoundError as exc:
        return {"status": "error", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# === Autopilot API ===

@app.get("/api/autopilot/status")
async def api_autopilot_status():
    return autopilot.get_status()

@app.post("/api/autopilot/start")
async def api_autopilot_start():
    autopilot.start()
    await log_activity("autopilot", "Autopilot started")
    return {"status": "started"}

@app.post("/api/autopilot/stop")
async def api_autopilot_stop():
    autopilot.stop()
    await log_activity("autopilot", "Autopilot stopped")
    return {"status": "stopped"}

@app.post("/api/autopilot/jobs/{name}/run")
async def api_autopilot_run_job(name: str):
    result = autopilot.run_job_now(name)
    await log_activity("autopilot", f"Manually ran job: {name} -> {result}")
    return {"status": result}

@app.post("/api/autopilot/jobs/{name}/toggle")
async def api_autopilot_toggle_job(name: str):
    jobs = get_jobs()
    job = next((j for j in jobs if j["name"] == name), None)
    if not job:
        raise HTTPException(404, "Job not found")
    new_state = not bool(job["enabled"])
    update_job(name, enabled=new_state)
    autopilot._sync_jobs()
    await log_activity("autopilot", f"Job '{name}' {'enabled' if new_state else 'disabled'}")
    return {"status": "toggled", "enabled": new_state}


# === Catalog API (Volt Records) ===

@app.get("/api/catalog/tracks")
async def api_catalog_tracks(
    bucket: str = "",
    key: str = "",
    brightness: str = "",
    hpi_min: float = 0.0,
    hpi_max: float = 10.0,
    bpm_min: float = 0.0,
    bpm_max: float = 999.0,
    search: str = "",
    limit: int = 200,
    offset: int = 0,
):
    return vault.get_catalog_tracks(
        bucket=bucket or None,
        key=key or None,
        brightness=brightness or None,
        hpi_min=hpi_min,
        hpi_max=hpi_max,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        search=search or None,
        limit=limit,
        offset=offset,
    )

@app.get("/api/catalog/tracks/{track_id}")
async def api_catalog_track(track_id: int):
    track = vault.get_track(track_id)
    if not track:
        raise HTTPException(404, "Track not found")
    return track

@app.get("/api/catalog/summary")
async def api_catalog_summary():
    return vault.get_catalog_summary()

@app.get("/api/catalog/top-prospects")
async def api_catalog_top_prospects(n: int = 6):
    return vault.get_top_prospects(n)

@app.get("/api/catalog/keys")
async def api_catalog_keys():
    return vault.get_catalog_by_key()

@app.get("/api/catalog/buckets")
async def api_catalog_buckets():
    return vault.get_catalog_by_bucket()

@app.get("/api/catalog/search")
async def api_catalog_search(q: str = "", limit: int = 50):
    if not q:
        raise HTTPException(400, "Query parameter 'q' is required")
    return vault.search_catalog(q, limit)


# === Health ===

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "agents": len(await get_agents()),
        "tasks": len(await get_tasks()),
        "plugins": len(await get_plugins()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=DEBUG)
