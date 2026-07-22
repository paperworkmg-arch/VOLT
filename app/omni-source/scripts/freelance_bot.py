#!/usr/bin/env python3
"""
Freelance Bot - Monitors job postings and sends desktop notifications
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
PINOKIO_TEMP = Path.home() / ".pinokio-temp"
STATE_FILE = Path(__file__).parent / "freelance_bot_state.json"

def load_state():
    """Load previously seen jobs"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"seen_files": [], "approved": [], "rejected": []}

def save_state(state):
    """Save state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def scan_jobs():
    """Scan for new job postings"""
    if not PINOKIO_TEMP.exists():
        return []
    
    jobs = []
    for f in PINOKIO_TEMP.glob("*.txt"):
        if f.name not in load_state().get("seen_files", []):
            # Parse job info from filename
            parts = f.stem.split('_', 2)
            if len(parts) >= 3:
                date = parts[0]
                time = parts[1]
                title = parts[2].replace('_', ' ')
            else:
                title = f.stem
            
            # Read first few lines for description
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    lines = file.readlines()[:5]
                    description = ' '.join(lines).strip()[:200]
            except:
                description = "No description available"
            
            jobs.append({
                'file': f.name,
                'title': title,
                'description': description,
                'created': datetime.fromtimestamp(f.stat().st_ctime).isoformat()
            })
    
    return jobs

def send_desktop_notification(title, message):
    """Send desktop notification"""
    try:
        # Use osascript for macOS
        cmd = [
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "default"'
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Failed to send notification: {e}")
        return False

def check_new_jobs():
    """Check for new jobs and notify"""
    state = load_state()
    new_jobs = scan_jobs()
    
    if not new_jobs:
        print("No new jobs found.")
        return
    
    print(f"Found {len(new_jobs)} new job(s)")
    
    # Send notification for each new job
    for job in new_jobs:
        title = f"New Freelance Job: {job['title']}"
        message = job['description'][:100] + "..." if len(job['description']) > 100 else job['description']
        send_desktop_notification(title, message)
        print(f"Notified: {job['title']}")
        
        # Mark as seen
        state["seen_files"].append(job['file'])
    
    save_state(state)

def approve_job(filename):
    """Approve a job"""
    state = load_state()
    if filename not in state["approved"]:
        state["approved"].append(filename)
        if filename in state["rejected"]:
            state["rejected"].remove(filename)
        save_state(state)
        print(f"Approved: {filename}")

def reject_job(filename):
    """Reject a job"""
    state = load_state()
    if filename not in state["rejected"]:
        state["rejected"].append(filename)
        if filename in state["approved"]:
            state["approved"].remove(filename)
        save_state(state)
        print(f"Rejected: {filename}")

def list_jobs():
    """List all jobs with status"""
    state = load_state()
    jobs = scan_jobs()
    
    print("\n=== Freelance Jobs ===\n")
    
    if not jobs:
        print("No jobs found.")
        return
    
    for job in jobs:
        status = "NEW"
        if job['file'] in state.get("approved", []):
            status = "APPROVED"
        elif job['file'] in state.get("rejected", []):
            status = "REJECTED"
        elif job['file'] in state.get("seen_files", []):
            status = "SEEN"
        
        print(f"[{status}] {job['title']}")
        print(f"  File: {job['file']}")
        print(f"  Description: {job['description'][:100]}...")
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python freelance_bot.py [check|list|approve|reject] [filename]")
        print("  check - Check for new jobs and send notifications")
        print("  list - List all jobs with status")
        print("  approve [filename] - Approve a job")
        print("  reject [filename] - Reject a job")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        check_new_jobs()
    elif command == "list":
        list_jobs()
    elif command == "approve":
        if len(sys.argv) < 3:
            print("Usage: python freelance_bot.py approve [filename]")
            sys.exit(1)
        approve_job(sys.argv[2])
    elif command == "reject":
        if len(sys.argv) < 3:
            print("Usage: python freelance_bot.py reject [filename]")
            sys.exit(1)
        reject_job(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
