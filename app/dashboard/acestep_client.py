"""ACE-Step engine client — talks to the staged launcher's backend.

The launcher (app/omni-source/pinokio/api/ace-step-ui.pinokio) runs the
ACE-Step 1.5 engine with its API enabled and wraps it in a simple local
flow: start a job, poll its status, download the finished song.

CONTRACT: the three endpoint paths below are the ONLY assumption this
client makes about that backend. During proof step 1 (engine alone),
check them against the launcher's README / a live call and adjust here —
nothing else in the patch needs to change.

    POST {base}/api/generate        -> {"job_id": "..."}
    GET  {base}/api/status/{job_id} -> {"status": "queued|running|complete|error", ...}
    GET  {base}/api/download/{job_id} -> audio bytes (flac/mp3)

Status words are normalised to: queued / running / complete / error.

All HTTP calls use trust_env=False: the hub only talks to localhost
services, and a stray proxy variable in the host environment must never
reroute or break them. Health probes never raise.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx

import acestep_config as cfg

CONTRACT = {
    "generate": "/api/generate",
    "status": "/api/status/{job_id}",
    "download": "/api/download/{job_id}",
    "health": "/",
}

_DONE = {"complete", "completed", "done", "success", "succeeded", "finished"}
_FAIL = {"error", "failed", "failure", "cancelled", "canceled"}


@dataclass
class AceJob:
    job_id: str
    status: str = "queued"          # queued | running | complete | error
    prompt: str = ""
    lyrics: str = ""
    params: dict = field(default_factory=dict)
    local_path: Path | None = None  # set once filed into the catalog inbox
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class AceStepError(RuntimeError):
    pass


class AceStepClient:
    """Async client for the launcher backend. One instance per hub process."""

    def __init__(self, base: str | None = None):
        self.base = (base or cfg.ACESTEP_API_BASE).rstrip("/")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=3.0) as http:
                r = await http.get(self.base + CONTRACT["health"])
                return r.status_code < 500
        except Exception:
            return False

    async def submit(self, *, prompt: str, lyrics: str = "", duration: int | None = None,
                     bpm: int | None = None, key_scale: str | None = None,
                     seed: int | None = None, audio_format: str | None = None) -> AceJob:
        duration = duration or cfg.ACESTEP_DEFAULT_DURATION
        if duration > cfg.ACESTEP_MAX_DURATION:
            raise AceStepError(
                f"duration {duration}s exceeds ACESTEP_MAX_DURATION "
                f"({cfg.ACESTEP_MAX_DURATION}s) — Air guardrail")
        payload = {
            "prompt": prompt,
            "lyrics": lyrics,
            "duration": duration,
            "audio_format": audio_format or cfg.ACESTEP_DEFAULT_FORMAT,
            "model": cfg.ACESTEP_MODEL,
            "planner": cfg.ACESTEP_PLANNER,
            "steps": cfg.ACESTEP_STEPS,
            "guidance": cfg.ACESTEP_GUIDANCE,
            "seed": seed if seed is not None else -1,
        }
        if bpm:
            payload["bpm"] = bpm
        if key_scale:
            payload["key_scale"] = key_scale
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=30.0) as http:
                r = await http.post(self.base + CONTRACT["generate"], json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise AceStepError(f"engine unreachable at {self.base}: {e}") from e
        job_id = data.get("job_id") or data.get("id") or uuid.uuid4().hex
        return AceJob(job_id=str(job_id), status="running",
                      prompt=prompt, lyrics=lyrics, params=payload)

    async def poll(self, job: AceJob) -> AceJob:
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=10.0) as http:
                r = await http.get(self.base + CONTRACT["status"].format(job_id=job.job_id))
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            job.status, job.error = "error", f"status check failed: {e}"
            return job
        raw = str(data.get("status", "running")).lower()
        if raw in _DONE:
            job.status = "complete"
        elif raw in _FAIL:
            job.status, job.error = "error", str(data.get("error") or raw)
        elif raw in ("queued", "pending", "waiting"):
            job.status = "queued"
        else:
            job.status = "running"
        return job

    async def download(self, job: AceJob, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        ext = (job.params.get("audio_format") or cfg.ACESTEP_DEFAULT_FORMAT).lower()
        dest = dest_dir / f"acestep_{job.job_id}.{ext}"
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=cfg.ACESTEP_JOB_TIMEOUT) as http:
                async with http.stream(
                        "GET", self.base + CONTRACT["download"].format(job_id=job.job_id)) as r:
                    r.raise_for_status()
                    with dest.open("wb") as f:
                        async for chunk in r.aiter_bytes(65536):
                            f.write(chunk)
        except httpx.HTTPError as e:
            raise AceStepError(f"download failed for job {job.job_id}: {e}") from e
        if dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)
            raise AceStepError(f"engine returned an empty file for job {job.job_id}")
        job.local_path = dest
        return dest
