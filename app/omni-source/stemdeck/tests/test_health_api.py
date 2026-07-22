from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoints_report_ok():
    from app.main import app

    with TestClient(app) as client:
        for path in ("/health", "/api/health"):
            r = client.get(path)
            assert r.status_code == 200
            body = r.json()
            assert body["name"] == "StemDeck"
            assert body["status"] == "ok"
            assert body["version"]
            assert "ffmpeg_configured" in body
            assert "jobs_dir" not in body
            assert "data_dir" not in body
