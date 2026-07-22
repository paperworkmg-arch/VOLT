"""Tests for sample scanner classification logic."""
from sample_scanner import classify_sample
from sampler_engine import _safe_filename


def test_classify_one_shot_by_name():
    assert classify_sample("/tmp/Kick_one_shot.wav") == "one-shot"
    assert classify_sample("/tmp/snare_hit.wav") == "one-shot"


def test_classify_loop_by_name():
    assert classify_sample("/tmp/drum_loop_120.wav") == "loop"


def test_classify_by_directory():
    assert classify_sample("/Drums/Kick.wav") == "one-shot"
    assert classify_sample("/Loops/groove.wav") == "loop"


def test_safe_filename():
    assert _safe_filename("My Cool Kit!") == "my-cool-kit"
    assert _safe_filename("Kit_123") == "kit_123"
