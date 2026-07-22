"""Tests for the Omni-Sampler engine."""
import asyncio
from pathlib import Path

import pytest

from sampler_engine import (
    _guess_drum_note, _parse_key, _safe_filename, build_sfz,
    create_kit, get_kit, delete_kit, export_kit
)
from sample_library import upsert_sample


def test_guess_drum_note():
    assert _guess_drum_note("Kick_808.wav") == 36
    assert _guess_drum_note("Snare.wav") == 38
    assert _guess_drum_note("Hat_Closed.wav") == 42


def test_parse_key():
    assert _parse_key("C major") == 60
    assert _parse_key("A minor") == 69
    assert _parse_key("") == 60


def test_safe_filename():
    assert _safe_filename("Big Kit!!") == "big-kit"


def test_build_sfz():
    sfz = build_sfz({
        "name": "Test Kit",
        "samples": [{
            "filename": "kick.wav",
            "midi_note": 36,
            "lo_note": 36,
            "hi_note": 36,
            "pitch_center": 36,
            "velocity_lo": 0,
            "velocity_hi": 127,
            "volume_db": 0.0,
        }]
    })
    assert "<region>" in sfz
    assert "sample=kick-wav.wav" in sfz
    assert "key=36" in sfz


def test_kit_lifecycle(tmp_path, monkeypatch):
    """Create, retrieve, export, and delete a kit."""
    import sample_library as sl
    monkeypatch.setattr(sl, "DB_PATH", tmp_path / "test_samples.db")
    sl._ensure_tables()

    async def _run():
        sample_id = await upsert_sample({
            "path": str(tmp_path / "kick.wav"),
            "filename": "kick.wav",
            "directory": str(tmp_path),
            "extension": ".wav",
            "size_bytes": 1000,
            "size_mb": 0.01,
            "sample_type": "one-shot",
        })
        (tmp_path / "kick.wav").write_bytes(b"RIFF" + b"\x00" * 100)

        kit_id = await create_kit("Test Kit", "A test kit", "drum", [sample_id])
        assert kit_id > 0

        kit = await get_kit(kit_id)
        assert kit["name"] == "Test Kit"
        assert len(kit["samples"]) == 1
        assert kit["samples"][0]["midi_note"] == 36

        import sampler_engine as se
        monkeypatch.setattr(se, "EXPORT_DIR", tmp_path / "exports")
        result = await export_kit(kit_id, "sfz")
        assert Path(result["zip"]).exists()

        await delete_kit(kit_id)
        assert await get_kit(kit_id) is None

    asyncio.run(_run())
