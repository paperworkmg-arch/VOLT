"""Swarm orchestrator — multi-agent parallel task execution."""
import asyncio
import json
import time
from datetime import datetime
import httpx
from database import (
    get_agents, get_db, update_agent_status, add_swarm_run,
    complete_swarm_run, log_activity
)
from config import (
    KIMI_API_KEY, KIMI_BASE_URL, OPENROUTER_API_KEY,
    OLLAMA_BASE_URL, XAI_API_KEY, GOOGLE_API_KEY, GEMINI_MODEL
)

PROVIDERS = {
    "kimi": {
        "base_url": KIMI_BASE_URL,
        "api_key": KIMI_API_KEY,
        "format": "anthropic",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
        "format": "openai",
    },
    "ollama": {
        "base_url": OLLAMA_BASE_URL,
        "api_key": "ollama",
        "format": "openai",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "api_key": XAI_API_KEY,
        "format": "openai",
    },
    "google": {
        "base_url": f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        "api_key": GOOGLE_API_KEY,
        "format": "google",
    },
}


def parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model_id)."""
    if "/" in model_str:
        parts = model_str.split("/", 1)
        return parts[0], parts[1]
    return "kimi", model_str


async def call_llm(provider: str, model: str, messages: list, system: str = "") -> str:
    """Call an LLM provider with automatic format detection."""
    cfg = PROVIDERS.get(provider, PROVIDERS["kimi"])

    if cfg["format"] == "anthropic":
        return await _call_anthropic(cfg, model, messages, system)
    elif cfg["format"] == "google":
        return await _call_google(cfg, messages, system)
    else:
        return await _call_openai(cfg, model, messages, system)


async def _call_anthropic(cfg: dict, model: str, messages: list, system: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}/v1/messages",
            headers={
                "x-api-key": cfg["api_key"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system or "You are a helpful AI assistant.",
                "messages": messages,
            },
        )
        data = resp.json()
        return data.get("content", [{}])[0].get("text", str(data))


async def _call_openai(cfg: dict, model: str, messages: list, system: str) -> str:
    if system:
        messages = [{"role": "system", "content": system}] + messages
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-type": "application/json",
            },
            json={"model": model, "messages": messages, "max_tokens": 4096},
        )
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", str(data))


async def _call_google(cfg: dict, messages: list, system: str) -> str:
    contents = []
    for m in messages:
        contents.append({"parts": [{"text": m["content"]}]})
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{cfg['base_url']}?key={cfg['api_key']}",
            json=payload,
        )
        data = resp.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", str(data))


class SwarmOrchestrator:
    """Decomposes objectives into subtasks, dispatches to agents, collects results."""

    def __init__(self):
        self.running = False

    async def run(self, objective: str, max_agents: int = 3) -> dict:
        """Execute a swarm run for the given objective."""
        self.running = True
        run_id = await add_swarm_run(objective)
        await log_activity("swarm", f"Swarm started: {objective}")

        agents = await get_agents()
        active_agents = [a for a in agents if a["status"] == "idle"][:max_agents]

        if not active_agents:
            await complete_swarm_run(run_id, "No idle agents available", "failed")
            return {"status": "failed", "reason": "No idle agents"}

        # Phase 1: Decompose
        agent_names = ", ".join([f"{a['name']}({a['role']})" for a in active_agents])
        plan_prompt = f"""You are Atlas, the orchestrator. Decompose this objective into subtasks.

Objective: {objective}

Available agents: {agent_names}

Return a JSON array of subtasks. Each subtask:
{{"task": "description", "agent": "agent_name", "priority": 1-5}}

Return ONLY valid JSON array, no other text."""

        plan_text = await call_llm(
            active_agents[0]["model"].split("/")[0],
            active_agents[0]["model"].split("/")[-1] if "/" in active_agents[0]["model"] else active_agents[0]["model"],
            [{"role": "user", "content": plan_prompt}],
            "You are a task decomposition expert. Return only valid JSON."
        )

        try:
            # Extract JSON from response
            plan_text = plan_text.strip()
            if "```" in plan_text:
                plan_text = plan_text.split("```")[1]
                if plan_text.startswith("json"):
                    plan_text = plan_text[4:]
            tasks = json.loads(plan_text)
        except (json.JSONDecodeError, IndexError):
            tasks = [{"task": objective, "agent": active_agents[0]["name"], "priority": 1}]

        # Phase 2: Dispatch in parallel
        agent_map = {a["name"]: a for a in active_agents}
        results = []

        async def execute_subtask(subtask: dict) -> dict:
            agent_name = subtask.get("agent", active_agents[0]["name"])
            agent = agent_map.get(agent_name, active_agents[0])
            model_str = agent["model"]
            prov, model_id = parse_model_string(model_str)

            await update_agent_status(agent["id"], "working")
            await log_activity("swarm", f"{agent['name']} assigned: {subtask['task'][:80]}")

            start = time.time()
            try:
                result = await call_llm(
                    prov, model_id,
                    [{"role": "user", "content": subtask["task"]}],
                    f"You are {agent['name']}, a {agent['role']} agent. Complete this task precisely."
                )
                elapsed = int((time.time() - start) * 1000)
                await update_agent_status(agent["id"], "idle")

                db = await get_db()
                await db.execute("UPDATE agents SET tasks_completed = tasks_completed + 1 WHERE id=?", (agent["id"],))
                await db.commit()
                await db.close()

                return {"agent": agent["name"], "task": subtask["task"], "result": result, "duration_ms": elapsed, "status": "success"}
            except Exception as e:
                await update_agent_status(agent["id"], "idle")
                return {"agent": agent["name"], "task": subtask["task"], "result": str(e), "status": "error"}

        # Run subtasks (limit concurrency)
        sem = asyncio.Semaphore(3)
        async def bounded(subtask):
            async with sem:
                return await execute_subtask(subtask)

        results = await asyncio.gather(*[bounded(t) for t in tasks])

        # Phase 3: Synthesize
        results_text = "\n".join([
            f"**{r['agent']}**: {r['result'][:500]}" for r in results if r["status"] == "success"
        ])

        complete_swarm_result = f"Completed {len([r for r in results if r['status']=='success'])}/{len(tasks)} subtasks.\n\n{results_text}"
        await complete_swarm_run(run_id, complete_swarm_result)
        await log_activity("swarm", f"Swarm completed: {objective[:80]}")

        self.running = False
        return {
            "status": "completed",
            "run_id": run_id,
            "objective": objective,
            "tasks": tasks,
            "results": results,
        }


swarm = SwarmOrchestrator()
