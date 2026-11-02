"""ACE-Step song-generation routes for the Omni-Studio hub (omni.py).

omni.py registers routes as decorators directly on the FastAPI app, so
this module exposes one registrar instead of an APIRouter:

    from acestep_routes import register_acestep_routes
    register_acestep_routes(app)          # see omni_hook_snippet.py

Endpoints
    GET  /api/acestep/health                 engine + ComfyUI reachability
    POST /api/acestep/generate               start a song job (engine surface)
    POST /api/acestep/generate/comfy         start a song job (ComfyUI surface)
    GET  /api/acestep/jobs/{job_id}          poll; on completion the song is
                                             filed to the catalog inbox as a
                                             DRAFT with a provenance sidecar
    GET  /api/acestep/jobs/{job_id}/download stream the filed audio

Catalog rule (unchanged from house policy): a generated track is a draft.
It enters the normal approval flow and passes the ownership/clearance
check before it is ever pitched. Provenance (surface, model, planner,
prompt, lyrics, seed, params) is stored with every file.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import acestep_config as cfg
from acestep_client import AceJob, AceStepClient, AceStepError
from comfyui_client import ComfyUIClient, ComfyUIError, build_workflow
from database import log_activity

_jobs: dict[str, AceJob] = {}
_filing: set[str] = set()
_engine = AceStepClient()
_comfy = ComfyUIClient()


class GenerateRequest(BaseModel):
    prompt: str
    lyrics: str = ""
    duration: int | None = None
    bpm: int | None = None
    key_scale: str | None = None
    seed: int | None = None
    audio_format: str | None = None


def _require_enabled() -> None:
    if not cfg.ACESTEP_ENABLED:
        raise HTTPException(503, "ACE-Step generation is switched off "
                                 "(ACESTEP_ENABLED=0)")


def _public(job: AceJob) -> dict:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "prompt": job.prompt,
        "surface": job.params.get("surface", "engine"),
        "file": str(job.local_path) if job.local_path else None,
        "error": job.error,
    }


async def _file_into_catalog(job: AceJob, audio_path: Path) -> Path:
    """Write the provenance sidecar beside the audio and log the draft.

    The hub's own POST /ingest (AudioMetadata: filename, archive_path)
    is the vault's front door; the attempt is best-effort so a schema
    mismatch there can never lose a finished render — the file and its
    sidecar are already in the inbox either way, and the outcome is
    recorded in the sidecar.
    """
    sidecar = {
        "job_id": job.job_id,
        "status": "draft",
        "filed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "audio_file": audio_path.name,
        "provenance": {
            "surface": job.params.get("surface", "engine"),
            "model": cfg.ACESTEP_MODEL,
            "planner": cfg.ACESTEP_PLANNER,
            "prompt": job.prompt,
            "lyrics": job.lyrics,
            "params": {k: v for k, v in job.params.items() if k != "surface"},
        },
        "clearance": "uncleared — draft, passes the normal check before any pitch",
        "ingest": "not attempted",
    }
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=10.0) as http:
            r = await http.post(
                f"http://127.0.0.1:{cfg.HUB_PORT}/ingest",
                json={"filename": audio_path.name,
                      "archive_path": str(audio_path)})
            sidecar["ingest"] = f"http {r.status_code}"
    except httpx.HTTPError as e:
        sidecar["ingest"] = f"failed: {e}"
    audio_path.with_suffix(audio_path.suffix + ".provenance.json").write_text(
        json.dumps(sidecar, indent=2))
    await log_activity("acestep",
                       f"Draft filed: {audio_path.name} "
                       f"({sidecar['provenance']['surface']}, ingest {sidecar['ingest']})")
    return audio_path


async def _maybe_file(job: AceJob) -> None:
    """When a job completes, pull its audio into the catalog inbox once."""
    if job.status != "complete" or job.local_path or job.job_id in _filing:
        return
    _filing.add(job.job_id)
    try:
        if job.params.get("surface") == "comfyui":
            state, entry = await _comfy.status(job.job_id)
            if state == "complete" and entry:
                path = await _comfy.download_first_audio(entry, cfg.ACESTEP_INBOX_DIR)
                job.local_path = await _file_into_catalog(job, path)
        else:
            path = await _engine.download(job, cfg.ACESTEP_INBOX_DIR)
            job.local_path = await _file_into_catalog(job, path)
    except (AceStepError, ComfyUIError) as e:
        job.error = str(e)
        await log_activity("acestep", f"Filing failed for {job.job_id}: {e}", "error")
    finally:
        _filing.discard(job.job_id)


async def _refresh(job: AceJob) -> AceJob:
    if job.status in ("complete", "error"):
        return job
    if time.time() - job.created_at > cfg.ACESTEP_JOB_TIMEOUT:
        job.status, job.error = "error", "job timed out"
        return job
    if job.params.get("surface") == "comfyui":
        state, _entry = await _comfy.status(job.job_id)
        job.status = state
    else:
        await _engine.poll(job)
    if job.status == "complete":
        await _maybe_file(job)
    return job


def register_acestep_routes(app) -> None:
    @app.get("/api/acestep/health")
    async def acestep_health():
        engine_up, comfy_up = await asyncio.gather(
            _engine.health(), _comfy.health())
        return {
            "enabled": cfg.ACESTEP_ENABLED,
            "engine": {"base": cfg.ACESTEP_API_BASE, "up": engine_up},
            "comfyui": {"base": cfg.COMFYUI_BASE, "up": comfy_up},
            "model": cfg.ACESTEP_MODEL,
            "planner": cfg.ACESTEP_PLANNER,
            "inbox": str(cfg.ACESTEP_INBOX_DIR),
        }

    @app.post("/api/acestep/generate")
    async def acestep_generate(req: GenerateRequest):
        _require_enabled()
        try:
            job = await _engine.submit(
                prompt=req.prompt, lyrics=req.lyrics, duration=req.duration,
                bpm=req.bpm, key_scale=req.key_scale, seed=req.seed,
                audio_format=req.audio_format)
        except AceStepError as e:
            raise HTTPException(502, str(e))
        job.params["surface"] = "engine"
        _jobs[job.job_id] = job
        await log_activity("acestep", f"Job {job.job_id} started (engine): "
                                      f"{req.prompt[:80]}")
        return _public(job)

    @app.post("/api/acestep/generate/comfy")
    async def acestep_generate_comfy(req: GenerateRequest):
        _require_enabled()
        workflow = build_workflow(
            prompt=req.prompt, lyrics=req.lyrics,
            duration=req.duration or cfg.ACESTEP_DEFAULT_DURATION,
            seed=req.seed if req.seed is not None else 0)
        try:
            prompt_id = await _comfy.submit(workflow)
        except ComfyUIError as e:
            raise HTTPException(502, str(e))
        job = AceJob(job_id=prompt_id, status="running", prompt=req.prompt,
                     lyrics=req.lyrics,
                     params={"surface": "comfyui", "duration": req.duration})
        _jobs[job.job_id] = job
        await log_activity("acestep", f"Job {job.job_id} started (comfyui): "
                                      f"{req.prompt[:80]}")
        return _public(job)

    @app.get("/api/acestep/jobs/{job_id}")
    async def acestep_job(job_id: str):
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "unknown job")
        return _public(await _refresh(job))

    @app.get("/api/acestep/jobs/{job_id}/download")
    async def acestep_download(job_id: str):
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "unknown job")
        await _refresh(job)
        if not job.local_path or not Path(job.local_path).exists():
            raise HTTPException(409, "song not filed yet")
        return FileResponse(str(job.local_path),
                            filename=Path(job.local_path).name)
