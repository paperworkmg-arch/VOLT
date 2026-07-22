"""
DAW Export Watcher — monitors Logic Pro export folders for new audio files.
Uploads to Google Drive and sends email notification.
"""
import os
import json
import time
import asyncio
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("daw_watcher")

# === Config ===
DAW_FOLDERS = [
    Path.home() / "Music" / "Logic",
    Path.home() / "Music" / "Logic" / "Bounces",
]
AUDIO_EXTENSIONS = {".aif", ".aiff", ".mp3", ".wav", ".flac", ".m4a", ".caf"}
STATE_FILE = Path(__file__).parent / "data" / "daw_watcher_state.json"
GOOGLE_DRIVE_FOLDER_NAME = "OMNI Exports"

# Google Drive setup
SERVICE_ACCOUNT_FILE = Path(__file__).parent / "data" / "service-account.json"


class DAWExportHandler(FileSystemEventHandler):
    """Handles new audio file events from watchdog."""

    def __init__(self, loop):
        self.loop = loop
        self.processed = self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"processed_files": [], "uploads": [], "last_scan": None}

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.processed, indent=2))

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in AUDIO_EXTENSIONS and not path.name.startswith("."):
            asyncio.run_coroutine_threadsafe(
                self._handle_new_file(path), self.loop
            )

    def on_moved(self, event):
        """Logic Pro often bounces to a temp file then moves it."""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if dest.suffix.lower() in AUDIO_EXTENSIONS and not dest.name.startswith("."):
            asyncio.run_coroutine_threadsafe(
                self._handle_new_file(dest), self.loop
            )

    async def _handle_new_file(self, path: Path):
        """Process a newly detected audio file."""
        file_key = str(path)
        if file_key in self.processed["processed_files"]:
            return

        # Wait for file to finish writing
        await asyncio.sleep(3)
        if not path.exists():
            return

        size_mb = path.stat().st_size / (1024 * 1024)
        logger.info(f"New export detected: {path.name} ({size_mb:.1f} MB)")

        result = {
            "file": path.name,
            "path": str(path),
            "size_mb": round(size_mb, 1),
            "detected_at": datetime.now().isoformat(),
            "upload_status": "pending",
            "email_status": "pending",
        }

        # Upload to Google Drive
        try:
            from google_drive import upload_to_drive
            drive_result = await upload_to_drive(path, GOOGLE_DRIVE_FOLDER_NAME)
            result["upload_status"] = "success"
            result["drive_url"] = drive_result.get("url", "")
            result["drive_id"] = drive_result.get("id", "")
            logger.info(f"Uploaded to Drive: {path.name}")
        except Exception as e:
            result["upload_status"] = "failed"
            result["upload_error"] = str(e)
            logger.error(f"Drive upload failed: {e}")

        # Send email notification
        try:
            from email_notifier import send_export_notification
            await send_export_notification(path.name, size_mb, result.get("drive_url", ""))
            result["email_status"] = "success"
            logger.info(f"Email sent for: {path.name}")
        except Exception as e:
            result["email_status"] = "failed"
            result["email_error"] = str(e)
            logger.error(f"Email failed: {e}")

        # Mark as processed
        self.processed["processed_files"].append(file_key)
        self.processed["uploads"].append(result)
        self.processed["last_scan"] = datetime.now().isoformat()
        self._save_state()


class DAWWatcher:
    """Main watcher that monitors DAW export folders."""

    def __init__(self):
        self.observer = Observer()
        self.running = False

    async def start(self):
        """Start watching DAW folders."""
        if self.running:
            return

        loop = asyncio.get_event_loop()
        handler = DAWExportHandler(loop)

        for folder in DAW_FOLDERS:
            if folder.exists():
                self.observer.schedule(handler, str(folder), recursive=True)
                logger.info(f"Watching: {folder}")

        self.observer.start()
        self.running = True
        logger.info("DAW watcher started")

    def stop(self):
        if self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            logger.info("DAW watcher stopped")

    def get_state(self):
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"processed_files": [], "uploads": [], "last_scan": None}

    async def scan_existing(self):
        """Scan existing files and report what's already there."""
        existing = []
        for folder in DAW_FOLDERS:
            if not folder.exists():
                continue
            for f in folder.iterdir():
                if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.startswith("."):
                    size_mb = f.stat().st_size / (1024 * 1024)
                    existing.append({
                        "file": f.name,
                        "path": str(f),
                        "size_mb": round(size_mb, 1),
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    })
        return existing


# Singleton
daw_watcher = DAWWatcher()
