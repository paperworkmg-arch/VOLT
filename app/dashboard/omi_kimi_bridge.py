#!/usr/bin/env python3
"""
Omi ↔ Kimi Bridge Middleware
Always-on receiver that batches ambient transcripts into daily local files,
then fires into Kimi's massive-context model for structured JSON extraction.
"""
import os, json, logging
from datetime import datetime
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent
OMI_LOG_DIR = BASE / "data" / "omi_logs"
OMI_LOG_DIR.mkdir(parents=True, exist_ok=True)

KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
MOONSHOT_URL = "https://api.moonshot.cn/v1/chat/completions"

class OmiPayload(BaseModel):
    session_id: str
    transcript: str
    timestamp: float

def get_daily_log_path():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return OMI_LOG_DIR / f"omi_{date_str}.txt"

async def receive_omi_transcript(payload: OmiPayload):
    """Append transcript to daily log file (zero data loss)."""
    log_path = get_daily_log_path()
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.fromtimestamp(payload.timestamp).isoformat()}] {payload.transcript}\n")
    
    logger.info(f"Logged {len(payload.transcript)} chars from Omi to {log_path}")
    return {"status": "logged", "chars": len(payload.transcript)}

async def process_daily_batch():
    """Process today's transcripts through Kimi 128k for structured extraction."""
    log_path = get_daily_log_path()
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="No transcript logs found for today.")

    with open(log_path, "r", encoding="utf-8") as f:
        daily_context = f.read()

    system_prompt = (
        "You are an automated extraction engine. Analyze this massive, unstructured transcript of the user's day. "
        "Extract: 1) Music IP/Lyrics/Melody ideas 2) CRM/Deal notes from meetings 3) SOPs or logic dictates. "
        "Return the output STRICTLY as valid JSON without markdown wrapping or pleasantries."
    )

    payload = {
        "model": "moonshot-v1-128k",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": daily_context}
        ],
        "temperature": 0.1
    }

    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info("Transmitting batch to Kimi 128k...")
            response = await client.post(MOONSHOT_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            raw_output = data['choices'][0]['message']['content']
            
            # Sanitize potential markdown fences
            clean_json_str = raw_output.strip().removeprefix("```json").removesuffix("```").strip()
            structured_data = json.loads(clean_json_str)

            # Archive structured output
            archive_path = log_path.with_suffix(".json")
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, indent=4)
                
            # Rename raw log to processed
            processed_path = log_path.with_name(log_path.stem + "_processed_raw.txt")
            os.rename(log_path, processed_path)

            logger.info(f"Extraction complete: {archive_path}")
            return {"status": "success", "archived_at": str(archive_path), "data": structured_data}

    except Exception as e:
        logger.error(f"Kimi API/Processing Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
