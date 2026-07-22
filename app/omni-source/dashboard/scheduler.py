"""Scheduler — cron-like task execution with auto-push results."""
import asyncio
import json
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import (
    get_db, get_tasks, update_task_status, add_task_result, log_activity
)
from swarm import call_llm, parse_model_string

scheduler = AsyncIOScheduler()


def parse_cron(expr: str) -> dict:
    """Parse '*/15 * * * *' into cron dict for APScheduler."""
    parts = expr.strip().split()
    if len(parts) != 5:
        return {"minute": "*", "hour": "*", "day": "*", "month": "*", "day_of_week": "*"}
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def execute_task(task_id: int, task_name: str, agent: str = "atlas"):
    """Execute a scheduled task — call the assigned agent and record results."""
    start = time.time()
    await update_task_status(task_id, "running", progress=0)
    await log_activity("scheduler", f"Task started: {task_name}")

    # Get agent model from DB
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT model FROM agents WHERE LOWER(name) = LOWER(?)", (agent,)
    )
    await db.close()

    model_str = row[0]["model"] if row else "kimi-for-coding/kimi-for-coding-highspeed"
    prov, model_id = parse_model_string(model_str)

    prompt = f"""You are executing a scheduled task. Be concise and structured.

Task: {task_name}
Time: {datetime.now().isoformat()}

Provide a brief status report with:
1. What was checked/done
2. Key findings
3. Any actions needed
4. Health status (green/yellow/red)"""

    try:
        result = await call_llm(
            prov, model_id,
            [{"role": "user", "content": prompt}],
            f"You are a system monitor agent. Report status concisely."
        )
        elapsed = int((time.time() - start) * 1000)
        await update_task_status(task_id, "completed", progress=100, result=result[:2000])
        await add_task_result(task_id, result, "success", elapsed)
        await log_activity("scheduler", f"Task completed: {task_name} ({elapsed}ms)")
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        await update_task_status(task_id, "failed", progress=0, result=str(e)[:2000])
        await add_task_result(task_id, str(e), "error", elapsed)
        await log_activity("scheduler", f"Task failed: {task_name}: {e}", "error")


async def sync_scheduled_tasks():
    """Reload scheduled tasks from DB and reschedule."""
    tasks = await get_tasks()

    # Remove existing jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("task_"):
            scheduler.remove_job(job.id)

    # Add enabled scheduled tasks
    for task in tasks:
        if task["type"] == "scheduled" and task["enabled"] and task["scheduled_cron"]:
            cron = parse_cron(task["scheduled_cron"])
            scheduler.add_job(
                execute_task,
                CronTrigger(**cron),
                args=[task["id"], task["name"], task.get("agent", "atlas")],
                id=f"task_{task['id']}",
                replace_existing=True,
            )
            await log_activity("scheduler", f"Scheduled: {task['name']} ({task['scheduled_cron']})")


def start_scheduler():
    """Start the APScheduler."""
    scheduler.start()


def stop_scheduler():
    """Stop the APScheduler."""
    scheduler.shutdown()
