"""ACE-Step engine client — talks to the staged launcher's backend.

Contract CONFIRMED 2026-11-02 from the launcher's own README + start.js
(app/omni-source/pinokio/api/ace-step-ui.pinokio, read on the Mac):

  - UI on 3000, backend on 3000's sibling 3001, engine API on 8001.
  - The backend (3001) is JWT-guarded. First call:
        POST /api/auth/setup {"username": ...}  -> {"token": ...}
    then send  Authorization: Bearer <token>  on everything else.
  - Start a job:   POST /api/generate            -> {"jobId": ...}
        body: {"customMode": bool, "songDescription": str,
               "instrumental": bool, "lyrics": str (custom mode)}
  - Poll status:   GET  /api/generate/status/{jobId}
  - There is NO download endpoint: finished audio is written by the
    backend to its public audio dir (app/server/public/audio) and the
    status payload carries the reference.
  - LIVE-CONFIRMED 2026-11-02 (proof step 2, real backend): terminal
    status is "succeeded"; the payload is
        {"status":"succeeded","result":{"audioUrls":["/audio/<file>.mp3"
        (or "/audio/<user-id>/<file>.mp3")],"duration":<sec>}}
    While running it carries {"etaSeconds": n, "stage": "..."}.
    "duration" IS honoured (30s/60s came back exact). Custom mode
    REQUIRES "style" (or lyrics/reference) — see submit(). Backend
    output is MP3 48 kHz stereo ~128 kbps. download() resolves the
    audioUrls reference and fetches it with the bearer token.
  - Engine runs as: acestep --enable-api --backend pt with
    ACESTEP_LM_OFFLOAD_TO_CPU=true (planner in system RAM) — the
    low-memory recipe is already the launcher's own setting.

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
    "setup": "/api/auth/setup",
    "generate": "/api/generate",
    "status": "/api/generate/status/{job_id}",
    "health": "/",
}

_DONE = {"complete", "completed", "done", "success", "succeeded", "finished"}
_FAIL = {"error", "failed", "failure", "cancelled", "canceled"}
_AUDIO_KEYS = ("audioUrls", "audio_urls", "audioUrl", "audio_url",
               "audioPath", "audio_path",
               "url", "file", "filename", "path", "output")


@dataclass
class AceJob:
    job_id: str
    status: str = "queued"          # queued | running | complete | error
    prompt: str = ""
    lyrics: str = ""
    params: dict = field(default_factory=dict)
    local_path: Path | None = None  # set once filed into the catalog inbox
    result_ref: str | None = None   # audio reference from the status payload
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class AceStepError(RuntimeError):
    pass


def _find_audio_ref(data: dict) -> str | None:
    """Search a status payload (incl. one level of nesting) for audio."""
    for source in (data, data.get("result") or {}, data.get("data") or {}):
        if not isinstance(source, dict):
            continue
        for key in _AUDIO_KEYS:
            val = source.get(key)
            if isinstance(val, list):  # live backend: result.audioUrls[]
                val = next((v for v in val if isinstance(v, str)), None)
            if isinstance(val, str) and val and (
                    "/" in val or val.lower().endswith((".flac", ".mp3", ".wav"))):
                return val
    return None


class AceStepClient:
    """Async client for the launcher backend. One instance per hub process."""

    def __init__(self, base: str | None = None):
        self.base = (base or cfg.ACESTEP_API_BASE).rstrip("/")
        self._token: str | None = None

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=3.0) as http:
                r = await http.get(self.base + CONTRACT["health"])
                return r.status_code < 500
        except Exception:
            return False

    async def _auth(self, http: httpx.AsyncClient, force: bool = False) -> str:
        if self._token and not force:
            return self._token
        r = await http.post(self.base + CONTRACT["setup"],
                            json={"username": cfg.ACESTEP_USERNAME})
        r.raise_for_status()
        token = r.json().get("token")
        if not token:
            raise AceStepError("launcher auth setup returned no token")
        self._token = str(token)
        return self._token

    async def _call(self, method: str, path: str, **kw) -> httpx.Response:
        """One authenticated call; on 401, re-setup once and retry."""
        async with httpx.AsyncClient(trust_env=False,
                                     timeout=kw.pop("timeout", 30.0)) as http:
            token = await self._auth(http)
            r = await http.request(method, self.base + path,
                                   headers={"Authorization": f"Bearer {token}"}, **kw)
            if r.status_code == 401:
                token = await self._auth(http, force=True)
                r = await http.request(method, self.base + path,
                                       headers={"Authorization": f"Bearer {token}"}, **kw)
            return r

    async def submit(self, *, prompt: str, lyrics: str = "", duration: int | None = None,
                     bpm: int | None = None, key_scale: str | None = None,
                     seed: int | None = None, audio_format: str | None = None) -> AceJob:
        duration = duration or cfg.ACESTEP_DEFAULT_DURATION
        if duration > cfg.ACESTEP_MAX_DURATION:
            raise AceStepError(
                f"duration {duration}s exceeds ACESTEP_MAX_DURATION "
                f"({cfg.ACESTEP_MAX_DURATION}s) — Air guardrail")
        payload = {
            # Live-confirmed 2026-11-02: custom mode REQUIRES a "style"
            # (or lyrics / reference audio) — an instrumental submit
            # without style is rejected. Always send style=prompt.
            "customMode": True,
            "songDescription": prompt,
            "style": prompt,
            "instrumental": not lyrics,
            "lyrics": lyrics,
            # Best-effort passthrough: honoured if the backend accepts
            # them, ignored otherwise (the README documents only the
            # four fields above). Confirm in proof step 2.
            "duration": duration,
            "audio_format": audio_format or cfg.ACESTEP_DEFAULT_FORMAT,
            "seed": seed if seed is not None else -1,
        }
        if bpm:
            payload["bpm"] = bpm
        if key_scale:
            payload["keyScale"] = key_scale
        try:
            r = await self._call("POST", CONTRACT["generate"], json=payload)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            raise AceStepError(f"engine backend unreachable at {self.base}: {e}") from e
        job_id = data.get("jobId") or data.get("job_id") or data.get("id") \
            or uuid.uuid4().hex
        return AceJob(job_id=str(job_id), status="running",
                      prompt=prompt, lyrics=lyrics, params=payload)

    async def poll(self, job: AceJob) -> AceJob:
        try:
            r = await self._call("GET", CONTRACT["status"].format(job_id=job.job_id),
                                 timeout=10.0)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            job.status, job.error = "error", f"status check failed: {e}"
            return job
        ref = _find_audio_ref(data)
        if ref:
            job.result_ref = ref
        raw = str(data.get("status", "running")).lower()
        if raw in _DONE or (ref and raw not in _FAIL):
            job.status = "complete"
        elif raw in _FAIL:
            job.status, job.error = "error", str(data.get("error") or raw)
        elif raw in ("queued", "pending", "waiting"):
            job.status = "queued"
        else:
            job.status = "running"
        return job

    async def download(self, job: AceJob, dest_dir: Path) -> Path:
        ref = job.result_ref
        if not ref:
            raise AceStepError(
                f"job {job.job_id} completed but its status payload carried "
                "no audio reference — check the payload shape against "
                "_find_audio_ref in acestep_client.py (proof step 2)")
        url = ref if ref.startswith("http") else (
            self.base + (ref if ref.startswith("/") else f"/audio/{ref}"))
        dest_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(ref.split("?")[0]).suffix or \
            f".{(job.params.get('audio_format') or cfg.ACESTEP_DEFAULT_FORMAT).lower()}"
        dest = dest_dir / f"acestep_{job.job_id}{ext}"
        try:
            async with httpx.AsyncClient(trust_env=False,
                                         timeout=cfg.ACESTEP_JOB_TIMEOUT) as http:
                token = await self._auth(http)
                async with http.stream(
                        "GET", url,
                        headers={"Authorization": f"Bearer {token}"}) as r:
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
