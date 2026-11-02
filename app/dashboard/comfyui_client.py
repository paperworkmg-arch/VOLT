"""ComfyUI client — second ACE-Step surface, driven by the hub.

ComfyUI's local API is stable and public:
    POST {base}/prompt                 -> {"prompt_id": "..."}
    GET  {base}/history/{prompt_id}    -> execution record + outputs
    GET  {base}/view?filename=..&subfolder=..&type=output -> file bytes

The workflow graph built here mirrors comfyui/acestep_text2song_lowmem.json
in this patch — same nodes, same low-memory recipe — so a song requested
from the VOLT front end and a graph dragged into ComfyUI by hand behave
the same. Node class names follow ComfyUI's native ACE-Step support;
if a future ComfyUI update renames a node, this builder is the one
place to fix.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import httpx

import acestep_config as cfg

# VERIFY at drop-in: the exact all-in-one Turbo checkpoint filename in
# ComfyUI's models/checkpoints folder on the machine that hosts ComfyUI.
CHECKPOINT = "ace_step_1.5_turbo_all_in_one.safetensors"


def build_workflow(*, prompt: str, lyrics: str = "", duration: int = 60,
                   seed: int = 0, steps: int | None = None,
                   guidance: float | None = None) -> dict:
    """Native ACE-Step text-to-song graph, low-memory (Turbo) recipe."""
    steps = steps or cfg.ACESTEP_STEPS
    guidance = cfg.ACESTEP_GUIDANCE if guidance is None else guidance
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "TextEncodeAceStepAudio",
              "inputs": {"clip": ["1", 1], "tags": prompt, "lyrics": lyrics}},
        "3": {"class_type": "ConditioningZeroOut",
              "inputs": {"conditioning": ["2", 0]}},
        "4": {"class_type": "EmptyAceStepLatentAudio",
              "inputs": {"seconds": float(duration), "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["2", 0],
                         "negative": ["3", 0], "latent_image": ["4", 0],
                         "seed": seed, "steps": steps, "cfg": guidance,
                         "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0}},
        "6": {"class_type": "VAEDecodeAudio",
              "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveAudioMP3",
              "inputs": {"audio": ["6", 0], "filename_prefix": "volt/acestep"}},
    }


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, base: str | None = None):
        self.base = (base or cfg.COMFYUI_BASE).rstrip("/")
        self.client_id = uuid.uuid4().hex

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=3.0) as http:
                r = await http.get(self.base + "/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    async def submit(self, workflow: dict) -> str:
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=30.0) as http:
                r = await http.post(self.base + "/prompt",
                                    json={"prompt": workflow,
                                          "client_id": self.client_id})
                r.raise_for_status()
                return str(r.json()["prompt_id"])
        except (httpx.HTTPError, KeyError) as e:
            raise ComfyUIError(f"ComfyUI submit failed at {self.base}: {e}") from e

    async def status(self, prompt_id: str) -> tuple[str, dict | None]:
        """Returns (queued|running|complete|error, history_entry|None)."""
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=10.0) as http:
                r = await http.get(self.base + f"/history/{prompt_id}")
                r.raise_for_status()
                hist = r.json()
        except httpx.HTTPError:
            return "running", None
        entry = hist.get(prompt_id)
        if not entry:
            return "running", None
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            return "error", entry
        if status.get("completed"):
            return "complete", entry
        return "running", entry

    async def download_first_audio(self, entry: dict, dest_dir: Path) -> Path:
        for node_out in (entry.get("outputs") or {}).values():
            for item in node_out.get("audio", []) or []:
                params = {"filename": item["filename"],
                          "subfolder": item.get("subfolder", ""),
                          "type": item.get("type", "output")}
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"acestep_comfy_{item['filename']}"
                async with httpx.AsyncClient(trust_env=False, timeout=cfg.ACESTEP_JOB_TIMEOUT) as http:
                    async with http.stream("GET", self.base + "/view", params=params) as r:
                        r.raise_for_status()
                        with dest.open("wb") as f:
                            async for chunk in r.aiter_bytes(65536):
                                f.write(chunk)
                if dest.stat().st_size == 0:
                    dest.unlink(missing_ok=True)
                    continue
                return dest
        raise ComfyUIError("ComfyUI job completed but produced no audio output")
