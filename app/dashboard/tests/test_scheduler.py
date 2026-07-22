"""Tests for scheduler utilities."""
import pytest
from scheduler import parse_cron


def test_parse_cron_valid():
    assert parse_cron("*/15 * * * *") == {
        "minute": "*/15",
        "hour": "*",
        "day": "*",
        "month": "*",
        "day_of_week": "*",
    }


def test_parse_cron_specific():
    assert parse_cron("0 9 * * 1-5") == {
        "minute": "0",
        "hour": "9",
        "day": "*",
        "month": "*",
        "day_of_week": "1-5",
    }


def test_parse_cron_invalid_falls_back():
    assert parse_cron("not-a-cron") == {
        "minute": "*",
        "hour": "*",
        "day": "*",
        "month": "*",
        "day_of_week": "*",
    }
