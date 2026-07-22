"""Tests for FastAPI app routes."""
import sys
from pathlib import Path

# Ensure dashboard is on path before importing app
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


def test_static_index_redirects_or_loads():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code in (200, 307, 308)
