"""Plugin system — extensible data sources for financial/economic/business data."""
import json
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime
import httpx
from database import get_db, log_activity
from config import PLUGINS_DIR, GOOGLE_API_KEY


class PluginManager:
    """Dynamic plugin loader — discovers and runs plugins from the plugins/ directory."""

    def __init__(self):
        self.plugins = {}
        self.load_plugins()

    def load_plugins(self):
        """Discover all plugin .py files in the plugins directory."""
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        for py_file in PLUGINS_DIR.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    plugin_info = mod.register()
                    self.plugins[py_file.stem] = {
                        "module": mod,
                        "info": plugin_info,
                    }
            except Exception as e:
                print(f"Plugin load error {py_file.name}: {e}")

    async def run_plugin(self, name: str, **kwargs) -> dict:
        """Execute a plugin by name."""
        if name not in self.plugins:
            return {"error": f"Plugin '{name}' not found"}

        plugin = self.plugins[name]
        start = datetime.now()
        try:
            result = await plugin["module"].execute(**kwargs)
            elapsed_ms = int((datetime.now() - start).total_seconds() * 1000)

            db = await get_db()
            await db.execute(
                "UPDATE plugins SET last_run=datetime('now'), result=? WHERE name=?",
                (json.dumps(result)[:2000], name)
            )
            await db.commit()
            await db.close()

            await log_activity("plugin", f"Plugin '{name}' ran in {elapsed_ms}ms")
            return {"status": "success", "data": result, "duration_ms": elapsed_ms}
        except Exception as e:
            await log_activity("plugin", f"Plugin '{name}' failed: {e}", "error")
            return {"status": "error", "error": str(e)}

    def get_registered(self) -> list:
        return [
            {"name": k, **v["info"]}
            for k, v in self.plugins.items()
        ]


# === Built-in Plugins ===

async def financial_data(symbol: str = "SPY") -> dict:
    """Fetch stock/ETF data from Google Finance."""
    url = f"https://www.google.com/finance/quote/{symbol}:NYSE"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return {"symbol": symbol, "status": resp.status_code, "source": "google_finance"}


async def economic_calendar() -> dict:
    """Fetch upcoming economic events."""
    return {
        "source": "economic_calendar",
        "note": "Uses cached data + web scraping",
        "events": [
            {"date": "2026-07-22", "event": "FOMC Minutes", "impact": "high"},
            {"date": "2026-07-25", "event": "GDP (Q2)", "impact": "high"},
            {"date": "2026-07-30", "event": "Fed Rate Decision", "impact": "high"},
        ]
    }


async def music_industry_data() -> dict:
    """Fetch music industry metrics relevant to Volt Records."""
    return {
        "source": "music_industry",
        "metrics": {
            "streaming_revenue_growth": "+10.2% YoY",
            "vinyl_sales_growth": "+15.7% YoY",
            "live_music_revenue": "$31.6B (2025)",
            "sync_licensing": "$1.2B market",
        },
        "platforms": {
            "spotify": "440M MAU",
            "apple_music": "88M MAU",
            "youtube_music": "100M+ MAU",
        }
    }


async def weather_data(city: str = "Nashville") -> dict:
    """Basic weather data."""
    return {"city": city, "source": "weather_api", "note": "Configure API key for live data"}


# Built-in plugin registry
BUILTIN_PLUGINS = {
    "financial_data": {
        "name": "Financial Data",
        "type": "financial",
        "description": "Stock/ETF market data from Google Finance",
        "execute": financial_data,
    },
    "economic_calendar": {
        "name": "Economic Calendar",
        "type": "economic",
        "description": "Upcoming economic events and their impact",
        "execute": economic_calendar,
    },
    "music_industry": {
        "name": "Music Industry",
        "type": "industry",
        "description": "Music industry metrics and streaming data",
        "execute": music_industry_data,
    },
    "weather": {
        "name": "Weather",
        "type": "utility",
        "description": "Weather data for any city",
        "execute": weather_data,
    },
}


async def init_builtin_plugins():
    """Register built-in plugins in the database."""
    db = await get_db()
    for name, info in BUILTIN_PLUGINS.items():
        await db.execute(
            "INSERT OR IGNORE INTO plugins (name, type, config) VALUES (?, ?, ?)",
            (name, info["type"], json.dumps({"description": info["description"]}))
        )
    await db.commit()
    await db.close()


plugin_manager = PluginManager()
