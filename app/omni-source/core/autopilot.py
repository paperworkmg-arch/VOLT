"""
Omni-Studio Autopilot — fully autonomous master orchestrator.

Discovers local modules, schedules them, runs them, retries failures, and reports
health back to the dashboard. Nothing manual.
"""
import json
import sqlite3
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Paths
STUDIO_DIR = Path(__file__).parent.parent
LOG_DIR = STUDIO_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STUDIO_DIR / "data" / "autopilot.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

PYTHON = sys.executable


@dataclass
class JobSpec:
    name: str
    script: str
    schedule: str  # 'every_N_minutes' or cron '*/15 * * * *'
    enabled: bool = True
    retries: int = 2
    timeout: int = 300
    category: str = "general"


DEFAULT_JOBS = [
    # Pipeline jobs are owned by the launchd master_orchestrator (core/master_orchestrator.py).
    # They stay disabled here so Autopilot never double-runs them; enable only if the orchestrator is retired.
    JobSpec("Lead Scraper", "integrations/scraper.py", "every_15_minutes", enabled=False, category="pipeline"),
    JobSpec("Income Watchdog", "scripts/income_watchdog.py", "every_10_minutes", enabled=False, category="pipeline"),
    JobSpec("Inbound Agent", "agents/inbound_agent.py", "every_5_minutes", enabled=False, category="pipeline"),
    JobSpec("AR Pitcher", "integrations/send_ar_pitches.py", "every_20_minutes", enabled=False, category="pipeline"),
    JobSpec("Sample Scanner", "dashboard/sample_scanner.py", "every_60_minutes", enabled=False, category="samples"),
    # Autopilot-native workflows
    JobSpec("Ghost Follow-Up", "agents/ghost_followup.py", "every_6_hours", category="pipeline"),
]


def init_db():
    """Initialize autopilot SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            name TEXT PRIMARY KEY,
            script TEXT NOT NULL,
            schedule TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            retries INTEGER DEFAULT 2,
            timeout INTEGER DEFAULT 300,
            category TEXT DEFAULT 'general',
            last_run TEXT,
            last_status TEXT,
            last_output TEXT,
            next_run TEXT,
            run_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT,
            status TEXT,
            output TEXT,
            duration_ms INTEGER,
            retry_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_runs_job ON runs(job_name);
        CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_jobs() -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs ORDER BY category, name").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_recent_runs(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def ensure_default_jobs():
    """Seed default jobs if none exist."""
    conn = sqlite3.connect(str(DB_PATH))
    existing = {r[0] for r in conn.execute("SELECT name FROM jobs")}
    for job in DEFAULT_JOBS:
        if job.name not in existing:
            conn.execute(
                """INSERT INTO jobs (name, script, schedule, enabled, retries, timeout, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job.name, job.script, job.schedule,
                 int(job.enabled), job.retries, job.timeout, job.category)
            )
    conn.commit()
    conn.close()


def update_job(name: str, enabled: Optional[bool] = None, schedule: Optional[str] = None):
    conn = sqlite3.connect(str(DB_PATH))
    if enabled is not None:
        conn.execute("UPDATE jobs SET enabled=? WHERE name=?", (int(enabled), name))
    if schedule is not None:
        conn.execute("UPDATE jobs SET schedule=? WHERE name=?", (schedule, name))
    conn.commit()
    conn.close()


def _parse_trigger(schedule: str):
    """Convert schedule string to APScheduler trigger."""
    if schedule.startswith("every_") and schedule.endswith("_minutes"):
        minutes = int(schedule.split("_")[1])
        return IntervalTrigger(minutes=minutes)
    if schedule.startswith("every_") and schedule.endswith("_hours"):
        hours = int(schedule.split("_")[1])
        return IntervalTrigger(hours=hours)
    parts = schedule.strip().split()
    if len(parts) == 5:
        return CronTrigger(
            minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]
        )
    # Default fallback
    return IntervalTrigger(minutes=15)


def _run_script(script: str, timeout: int) -> tuple[str, str, int]:
    """Run a script and return stdout, stderr, returncode."""
    script_path = STUDIO_DIR / script
    if not script_path.exists():
        return "", f"Script not found: {script_path}", 127

    try:
        proc = subprocess.run(
            [PYTHON, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(STUDIO_DIR),
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout}s", 124
    except Exception as exc:
        return "", f"Exception: {exc}\n{traceback.format_exc()}", 1


def _execute_job(name: str, script: str, timeout: int, max_retries: int):
    """Execute a job with retries and logging."""
    conn = sqlite3.connect(str(DB_PATH))
    started = datetime.now()
    status = "failed"
    output = ""
    retry = 0

    while retry <= max_retries:
        stdout, stderr, rc = _run_script(script, timeout)
        output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        if rc == 0:
            status = "success"
            break
        retry += 1
        if retry <= max_retries:
            time.sleep(2 ** retry)  # exponential backoff

    finished = datetime.now()
    duration_ms = int((finished - started).total_seconds() * 1000)

    conn.execute(
        """INSERT INTO runs (job_name, started_at, finished_at, status, output, duration_ms, retry_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, started.isoformat(), finished.isoformat(), status, output, duration_ms, retry)
    )
    conn.execute(
        """UPDATE jobs SET last_run=?, last_status=?, last_output=?,
           run_count = run_count + ?,
           fail_count = fail_count + ?
           WHERE name=?""",
        (finished.isoformat(), status, output[:2000],
         1, 0 if status == "success" else 1, name)
    )
    conn.commit()
    conn.close()
    return status


class Autopilot:
    """Autonomous orchestrator for Omni-Studio."""

    def __init__(self):
        init_db()
        ensure_default_jobs()
        self.scheduler = AsyncIOScheduler()
        self.running = False

    def _sync_jobs(self):
        """Reload jobs from DB and reschedule."""
        # Remove existing jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("autopilot_"):
                self.scheduler.remove_job(job.id)

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM jobs WHERE enabled=1").fetchall()
        conn.close()

        for row in rows:
            rowd = _row_to_dict(row)
            self.scheduler.add_job(
                _execute_job,
                _parse_trigger(rowd["schedule"]),
                args=[rowd["name"], rowd["script"], rowd["timeout"], rowd["retries"]],
                id=f"autopilot_{rowd['name']}",
                replace_existing=True,
            )

    def start(self):
        if self.running:
            return
        self._sync_jobs()
        self.scheduler.start()
        self.running = True

    def stop(self):
        if not self.running:
            return
        self.scheduler.shutdown()
        self.running = False

    def run_job_now(self, name: str) -> str:
        """Trigger a job immediately (blocking)."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE name=?", (name,)).fetchone()
        conn.close()
        if not row:
            return "not_found"
        rowd = _row_to_dict(row)
        return _execute_job(rowd["name"], rowd["script"], rowd["timeout"], rowd["retries"])

    def get_status(self) -> dict:
        return {
            "running": self.running,
            "jobs": get_jobs(),
            "recent_runs": get_recent_runs(20),
        }


# Singleton
autopilot = Autopilot()


if __name__ == "__main__":
    import asyncio
    ap = Autopilot()
    ap.start()
    print("Autopilot running. Press Ctrl+C to stop.")
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        ap.stop()
        print("Autopilot stopped.")
