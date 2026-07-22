#!/usr/bin/env python3
"""
Kimi ↔ Omni-Studio Bridge
Bidirectional communication between Kimi app and Omni-Studio dashboard.
"""
import os, json, time, asyncio
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
BRIDGE_DIR = BASE / "data" / "bridge"
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

# === Kimi → Omni-Studio ===

async def kimi_to_omni(task_type: str, payload: dict) -> dict:
    """Receive task from Kimi app and route to Omni-Studio."""
    from omni import log_activity, swarm_run, call_llm, parse_model
    
    await log_activity("bridge", f"Kimi → Omni: {task_type}")
    
    if task_type == "swarm":
        result = await swarm_run(payload.get("objective", ""), max_agents=payload.get("max_agents", 3))
        return {"status": "routed", "type": "swarm", "result": result}
    
    elif task_type == "agent":
        agent_name = payload.get("agent", "atlas")
        message = payload.get("message", "")
        from omni import get_agents, update_agent
        agents = await get_agents()
        agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
        if not agent:
            return {"status": "error", "message": f"Agent {agent_name} not found"}
        
        prov, model = parse_model(agent["model"])
        await update_agent(agent["id"], "working")
        try:
            result = await call_llm(prov, model, [{"role": "user", "content": message}],
                                    f"You are {agent['name']}, a {agent['role']}.")
            await update_agent(agent["id"], "idle")
            return {"status": "success", "type": "agent", "agent": agent_name, "result": result}
        except Exception as e:
            await update_agent(agent["id"], "idle")
            return {"status": "error", "message": str(e)}
    
    elif task_type == "chat":
        from omni import call_llm, parse_model
        message = payload.get("message", "")
        provider = payload.get("provider", "kimi")
        prov, model = parse_model(provider + "/k2p7") if "/" not in provider else parse_model(provider)
        result = await call_llm(prov, model, [{"role": "user", "content": message}])
        return {"status": "success", "type": "chat", "result": result}
    
    elif task_type == "status":
        from omni import get_agents, get_tasks, get_activity
        return {
            "status": "success",
            "type": "status",
            "agents": await get_agents(),
            "tasks": await get_tasks(),
            "activity": await get_activity(10)
        }
    
    return {"status": "error", "message": f"Unknown task type: {task_type}"}


# === Omni-Studio → Kimi ===

async def omni_to_kimi(prompt: str, callback_url: str = None) -> dict:
    """Send work to Kimi app. If callback_url provided, Kimi will POST result there."""
    task_id = f"kimi_{int(time.time() * 1000)}"
    
    task = {
        "id": task_id,
        "prompt": prompt,
        "callback_url": callback_url,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    # Save task to queue
    task_file = BRIDGE_DIR / f"{task_id}.json"
    task_file.write_text(json.dumps(task, indent=2))
    
    # Also create a symlink in pending folder
    pending_dir = BRIDGE_DIR / "pending"
    pending_dir.mkdir(exist_ok=True)
    (pending_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2))
    
    return {"status": "queued", "task_id": task_id, "message": "Task queued for Kimi"}


async def get_kimi_tasks() -> list:
    """Get pending tasks for Kimi to process."""
    pending_dir = BRIDGE_DIR / "pending"
    if not pending_dir.exists():
        return []
    
    tasks = []
    for f in pending_dir.glob("*.json"):
        try:
            task = json.loads(f.read_text())
            tasks.append(task)
        except:
            pass
    return tasks


async def complete_kimi_task(task_id: str, result: str) -> dict:
    """Mark a Kimi task as completed."""
    pending_file = BRIDGE_DIR / "pending" / f"{task_id}.json"
    task_file = BRIDGE_DIR / f"{task_id}.json"
    
    if not task_file.exists():
        return {"status": "error", "message": "Task not found"}
    
    task = json.loads(task_file.read_text())
    task["status"] = "completed"
    task["result"] = result
    task["completed_at"] = datetime.now().isoformat()
    
    task_file.write_text(json.dumps(task, indent=2))
    
    # Move from pending to completed
    completed_dir = BRIDGE_DIR / "completed"
    completed_dir.mkdir(exist_ok=True)
    (completed_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2))
    
    if pending_file.exists():
        pending_file.unlink()
    
    # Call callback if provided
    if task.get("callback_url"):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(task["callback_url"], json=task)
        except:
            pass
    
    return {"status": "completed", "task_id": task_id}
