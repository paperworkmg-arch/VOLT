"""
llm_router.py — Shared LLM routing with circuit breaker + auto-fallback.

When a provider hits rate limits, errors, or timeouts, requests automatically
route to the next healthy provider in the fallback chain.
"""

import asyncio
import json
import time
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("llm-router")

# ─── Circuit Breaker States ───────────────────────────────────────────────────

class State(str, Enum):
    CLOSED = "closed"       # Normal — requests pass through
    OPEN = "open"           # Failing — requests blocked
    HALF_OPEN = "half_open" # Testing — one request allowed through

# ─── Per-Provider Circuit Breaker ─────────────────────────────────────────────

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0
        self.last_error: str = ""

    def record_success(self):
        self.failure_count = 0
        self.success_count += 1
        if self.state == State.HALF_OPEN:
            logger.info("Circuit breaker: HALF_OPEN → CLOSED (recovered)")
            self.state = State.CLOSED

    def record_failure(self, error: str = ""):
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.last_error = error
        if self.failure_count >= self.failure_threshold:
            if self.state != State.OPEN:
                logger.warning(f"Circuit breaker: → OPEN after {self.failure_count} failures")
            self.state = State.OPEN

    def allow_request(self) -> bool:
        if self.state == State.CLOSED:
            return True
        if self.state == State.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker: OPEN → HALF_OPEN (testing)")
                self.state = State.HALF_OPEN
                return True
            return False
        if self.state == State.HALF_OPEN:
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_error": self.last_error,
        }

# ─── Provider Config ──────────────────────────────────────────────────────────

PROVIDERS = {
    "kimi": {
        "base_url": "https://api.kimi.com/coding",
        "format": "anthropic",
        "priority": 0,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "format": "openai",
        "priority": 1,
    },
    "google": {
        "base_url": "generativelanguage.googleapis.com",
        "format": "google",
        "priority": 2,
        "models": ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "format": "openai",
        "priority": 3,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "format": "openai",
        "priority": 99,
    },
}

# ─── Router State ─────────────────────────────────────────────────────────────

_breakers: dict[str, CircuitBreaker] = {}
_provider_keys: dict[str, str] = {}  # populated from env at init

def _init_provider_keys():
    """Load API keys from environment."""
    import os
    global _provider_keys
    _provider_keys = {
        "kimi": os.getenv("KIMI_API_KEY", ""),
        "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
        "google": os.getenv("GOOGLE_API_KEY", ""),
        "xai": os.getenv("XAI_API_KEY", ""),
        "ollama": "ollama",
    }

def _get_breaker(provider: str) -> CircuitBreaker:
    if provider not in _breakers:
        threshold = 3 if provider != "ollama" else 999  # never break ollama
        _breakers[provider] = CircuitBreaker(failure_threshold=threshold, recovery_timeout=60.0)
    return _breakers[provider]

def _has_key(provider: str) -> bool:
    if not _provider_keys:
        _init_provider_keys()
    return bool(_provider_keys.get(provider, ""))

def _fallback_order(primary: str) -> list[str]:
    """Return providers sorted by priority, primary first, skipping those without keys."""
    if not _provider_keys:
        _init_provider_keys()
    others = sorted(
        [p for p in PROVIDERS if p != primary and _has_key(p)],
        key=lambda p: PROVIDERS[p]["priority"],
    )
    return [primary] + others

# ─── Model Parsing ────────────────────────────────────────────────────────────

def parse_model(model_str: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model_id). Default provider: kimi."""
    if "/" in model_str:
        p, m = model_str.split("/", 1)
        return p, m
    return "kimi", model_str

# ─── LLM Callers ──────────────────────────────────────────────────────────────

async def _call_anthropic(cfg: dict, api_key: str, model: str, messages: list, system: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system or "You are a helpful assistant.",
                "messages": messages,
            },
        )
        if resp.status_code == 429:
            raise RateLimitError(f"429 rate limit from {model}")
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data.get("content", [{}])[0].get("text", str(data))


async def _call_openai(cfg: dict, api_key: str, model: str, messages: list, system: str) -> str:
    if system:
        messages = [{"role": "system", "content": system}] + messages
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 4096},
        )
        if resp.status_code == 429:
            raise RateLimitError(f"429 rate limit from {model}")
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", str(data))


async def _call_google(cfg: dict, api_key: str, model: str, messages: list, system: str) -> str:
    contents = [{"parts": [{"text": m["content"]}]} for m in messages]
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{url}?key={api_key}", json=payload)
        if resp.status_code == 429:
            raise RateLimitError(f"429 rate limit from {model}")
        if resp.status_code >= 400:
            raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", str(data))


async def _call_provider(provider: str, model: str, messages: list, system: str) -> str:
    cfg = PROVIDERS[provider]
    api_key = _provider_keys.get(provider, "")
    if not api_key and provider != "ollama":
        raise ProviderError(f"No API key for {provider}")
    if cfg["format"] == "anthropic":
        return await _call_anthropic(cfg, api_key, model, messages, system)
    elif cfg["format"] == "google":
        return await _call_google(cfg, api_key, model, messages, system)
    else:
        return await _call_openai(cfg, api_key, model, messages, system)

# ─── Custom Errors ────────────────────────────────────────────────────────────

class ProviderError(Exception):
    pass

class RateLimitError(ProviderError):
    pass

class AllProvidersFailedError(Exception):
    def __init__(self, results: dict[str, str]):
        self.results = results
        summary = "; ".join(f"{k}: {v}" for k, v in results.items())
        super().__init__(f"All providers failed: {summary}")

# ─── Main Entry Point ─────────────────────────────────────────────────────────

async def call_llm(
    provider: str,
    model: str,
    messages: list,
    system: str = "",
) -> str:
    """
    Call an LLM with automatic circuit-breaking and fallback.

    Tries the primary provider first. If it fails (rate limit, error, timeout),
    automatically falls back to the next healthy provider in the priority chain.
    """
    order = _fallback_order(provider)
    errors: dict[str, str] = {}

    for p in order:
        breaker = _get_breaker(p)
        if not breaker.allow_request():
            logger.debug(f"Skipping {p}: circuit breaker OPEN (last error: {breaker.last_error})")
            errors[p] = f"circuit breaker open: {breaker.last_error}"
            continue

        try:
            result = await _call_provider(p, model, messages, system)
            breaker.record_success()
            if p != provider:
                logger.info(f"Fallback success: {provider} → {p} (model={model})")
            return result
        except RateLimitError as e:
            logger.warning(f"Rate limit on {p}: {e}")
            breaker.record_failure(str(e))
            errors[p] = str(e)
        except ProviderError as e:
            logger.warning(f"Provider error on {p}: {e}")
            breaker.record_failure(str(e))
            errors[p] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error on {p}: {e}")
            breaker.record_failure(str(e))
            errors[p] = str(e)

    raise AllProvidersFailedError(errors)

# ─── Health Status ────────────────────────────────────────────────────────────

def get_health() -> dict:
    """Return circuit breaker status for all providers."""
    if not _provider_keys:
        _init_provider_keys()
    result = {}
    for name in PROVIDERS:
        b = _get_breaker(name)
        result[name] = {
            **b.to_dict(),
            "has_key": _has_key(name),
            "priority": PROVIDERS[name]["priority"],
        }
    return result
