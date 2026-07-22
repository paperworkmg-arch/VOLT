"""Pytest configuration for the Omni-Studio dashboard."""
import sys
from pathlib import Path

# Ensure dashboard modules can be imported during tests
DASHBOARD_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))
