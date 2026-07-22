#!/usr/bin/env python3
"""Tests for music_library_aggregator.py — runs in dry-run mode, no API keys needed."""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.expanduser('~/Omni-Studio'))
sys.path.insert(0, os.path.expanduser('~/Omni-Studio/agents'))

import music_library_aggregator as mla

FIXTURES = os.path.expanduser('~/Omni-Studio/tests/fixtures')


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    original = mla.DB_PATH
    mla.DB_PATH = path
    yield path
    mla.DB_PATH = original
    os.unlink(path)


@pytest.fixture(autouse=True)
def enable_dry_run():
    original = mla.DRY_RUN
    mla.DRY_RUN = True
    yield
    mla.DRY_RUN = original


class TestBuildDork:
    def test_contains_site_filter(self):
        dork = mla.build_dork('KPM')
        assert 'site:linkedin.com/in/' in dork

    def test_contains_library_name(self):
        dork = mla.build_dork('Bruton')
        assert '"Bruton"' in dork

    def test_contains_role_or_group(self):
        dork = mla.build_dork('KPM')
        assert 'A&R' in dork
        assert 'Creative Director' in dork
        assert 'Catalog Manager' in dork
        assert 'OR' in dork

    def test_special_characters_not_escaped(self):
        dork = mla.build_dork("O'Connor")
        assert "O'Connor" in dork


class TestTargetModel:
    def test_valid_target(self):
        t = mla.Target(
            name="Jane Doe",
            title="A&R Manager",
            sub_library="KPM",
            linkedin_url="https://linkedin.com/in/jane-doe"
        )
        assert t.name == "Jane Doe"
        assert t.sub_library == "KPM"

    def test_target_list_roundtrip(self):
        tl = mla.TargetList(targets=[
            mla.Target(name="A", title="B", sub_library="C", linkedin_url="https://linkedin.com/in/a")
        ])
        assert len(tl.targets) == 1
        assert tl.targets[0].name == "A"


class TestEnsureDb:
    def test_creates_table(self, temp_db):
        mla.ensure_db()
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self, temp_db):
        mla.ensure_db()
        mla.ensure_db()
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        assert cursor.fetchone()[0] == 0
        conn.close()


class TestSaveTargets:
    def test_insert_returns_count(self, temp_db):
        mla.ensure_db()
        targets = [
            {"name": "Jane", "title": "A&R", "sub_library": "KPM",
             "linkedin_url": "https://linkedin.com/in/jane"},
            {"name": "John", "title": "CD", "sub_library": "FirstCom",
             "linkedin_url": "https://linkedin.com/in/john"},
        ]
        count = mla.save_targets(targets)
        assert count == 2

    def test_duplicate_url_skipped(self, temp_db):
        mla.ensure_db()
        t = {"name": "Jane", "title": "A&R", "sub_library": "KPM",
             "linkedin_url": "https://linkedin.com/in/jane"}
        mla.save_targets([t])
        count = mla.save_targets([t])
        assert count == 0
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_saved_rows_have_correct_status(self, temp_db):
        mla.ensure_db()
        mla.save_targets([{"name": "X", "title": "Y", "sub_library": "Z",
                           "linkedin_url": "https://linkedin.com/in/x"}])
        conn = sqlite3.connect(temp_db)
        row = conn.execute("SELECT status, source FROM leads WHERE name='X'").fetchone()
        assert row[0] == 'MUSIC_LIBRARY_TARGET'
        assert row[1] == 'MUSIC_LIBRARY_TARGET'
        conn.close()

    def test_multiple_inserts_unique_urls(self, temp_db):
        mla.ensure_db()
        targets = [
            {"name": f"User{i}", "title": "A&R", "sub_library": "KPM",
             "linkedin_url": f"https://linkedin.com/in/user{i}"}
            for i in range(50)
        ]
        count = mla.save_targets(targets)
        assert count == 50
        conn = sqlite3.connect(temp_db)
        assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 50
        conn.close()


class TestDryRunMode:
    def test_dork_linkedin_returns_fixture(self):
        results = asyncio.run(mla.dork_linkedin(None, 'KPM'))
        assert isinstance(results, list)
        assert len(results) >= 1
        assert 'link' in results[0] or 'title' in results[0]

    def test_extract_targets_returns_fixture(self):
        targets = mla.extract_targets([], 'KPM')
        assert isinstance(targets, list)
        assert len(targets) >= 1
        assert targets[0]['sub_library'] == 'KPM'
        assert 'linkedin_url' in targets[0]

    def test_full_dry_run_pipeline(self, temp_db):
        mla.ensure_db()
        total = 0
        for lib in ['KPM', 'FirstCom', 'Bruton']:
            raw = asyncio.run(mla.dork_linkedin(None, lib))
            assert len(raw) > 0
            targets = mla.extract_targets(raw, lib)
            inserted = mla.save_targets(targets)
            total += inserted
        assert total == 3
        conn = sqlite3.connect(temp_db)
        assert conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 3
        conn.close()


class TestSerperFixtureParsing:
    def test_fixture_loads(self):
        path = os.path.join(FIXTURES, 'serper_sample.json')
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 3
        for item in data:
            assert 'title' in item
            assert 'link' in item
            assert 'linkedin.com' in item['link']

    def test_fixture_has_diverse_libraries(self):
        path = os.path.join(FIXTURES, 'serper_sample.json')
        with open(path) as f:
            data = json.load(f)
        libraries = {item['title'].split(' - ')[2].split(' |')[0] for item in data}
        assert len(libraries) == 3
        assert 'KPM Music' in libraries
        assert 'FirstCom Music' in libraries


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
