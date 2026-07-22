"""Tests for dashboard configuration."""
import os


def test_config_does_not_contain_hardcoded_secrets():
    """Ensure config.py contains no hardcoded OAuth secrets."""
    from config import GOOGLE_OAUTH
    assert isinstance(GOOGLE_OAUTH, dict)
    # When env vars are unset, no clients should be configured
    assert GOOGLE_OAUTH == {}


def test_config_reads_oauth_from_env(monkeypatch):
    """OAuth client details must be loaded from environment variables."""
    monkeypatch.setenv("GOOGLE_OAUTH_OMNI_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_OMNI_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_OMNI_PROJECT_ID", "test-project")

    # Force reimport by clearing cache
    import sys
    if "config" in sys.modules:
        del sys.modules["config"]
    from config import GOOGLE_OAUTH

    assert "omni" in GOOGLE_OAUTH
    assert GOOGLE_OAUTH["omni"]["client_id"] == "test-client-id"
    assert GOOGLE_OAUTH["omni"]["client_secret"] == "test-client-secret"
    assert GOOGLE_OAUTH["omni"]["project_id"] == "test-project"


def test_config_host_port_env(monkeypatch):
    """Server bind address can be overridden from env."""
    monkeypatch.setenv("OMNI_HOST", "127.0.0.1")
    monkeypatch.setenv("OMNI_PORT", "9000")
    monkeypatch.setenv("OMNI_DEBUG", "false")

    import sys
    if "config" in sys.modules:
        del sys.modules["config"]
    from config import HOST, PORT, DEBUG

    assert HOST == "127.0.0.1"
    assert PORT == 9000
    assert DEBUG is False
