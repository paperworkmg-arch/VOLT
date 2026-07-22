#!/usr/bin/env python3
"""
Automated Approval Monitor
Checks pending approvals from CRM/agents and sends desktop notifications
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
OMNI_SOURCE = Path(__file__).parent.parent
CONFIG_DIR = OMNI_SOURCE / "config"
DATA_DIR = OMNI_SOURCE / "data"
CRM_DB = DATA_DIR / "business" / "crm.db"

def get_pending_approvals():
    """Get all pending approvals from CRM database"""
    approvals = []
    
    if not CRM_DB.exists():
        return approvals
    
    try:
        conn = sqlite3.connect(str(CRM_DB))
        cursor = conn.cursor()
        
        # Check for pending client approvals
        cursor.execute("""
            SELECT id, client_name, status, notes, created_at 
            FROM clients 
            WHERE status = 'pending_approval'
        """)
        for row in cursor.fetchall():
            approvals.append({
                'type': 'client',
                'id': row[0],
                'name': row[1],
                'status': row[2],
                'notes': row[3],
                'created_at': row[4]
            })
        
        # Check for pending invoice approvals
        cursor.execute("""
            SELECT id, client_name, amount, status, created_at 
            FROM invoices 
            WHERE status = 'pending_approval'
        """)
        for row in cursor.fetchall():
            approvals.append({
                'type': 'invoice',
                'id': row[0],
                'name': row[1],
                'amount': row[2],
                'status': row[3],
                'created_at': row[4]
            })
        
        # Check for pending content approvals
        cursor.execute("""
            SELECT id, title, platform, status, created_at 
            FROM content 
            WHERE status = 'pending_approval'
        """)
        for row in cursor.fetchall():
            approvals.append({
                'type': 'content',
                'id': row[0],
                'name': row[1],
                'platform': row[2],
                'status': row[3],
                'created_at': row[4]
            })
        
        conn.close()
    except Exception as e:
        print(f"Error reading CRM database: {e}")
    
    return approvals

def send_desktop_notification(title, message, priority="normal"):
    """Send desktop notification via Pinokio pterm"""
    try:
        # Use pterm push for desktop notifications
        cmd = ["pterm", "push", title, message]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        # Fallback to macOS notifications
        try:
            cmd = [
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except Exception as e:
            print(f"Failed to send notification: {e}")
            return False

def check_and_notify():
    """Main function to check approvals and send notifications"""
    print(f"[{datetime.now()}] Checking pending approvals...")
    
    approvals = get_pending_approvals()
    
    if not approvals:
        print("No pending approvals found.")
        return
    
    print(f"Found {len(approvals)} pending approval(s)")
    
    # Group by type
    by_type = {}
    for approval in approvals:
        app_type = approval['type']
        if app_type not in by_type:
            by_type[app_type] = []
        by_type[app_type].append(approval)
    
    # Send notifications for each type
    for app_type, items in by_type.items():
        count = len(items)
        title = f"Omni Studio - {count} Pending {app_type.title()} Approval(s)"
        
        # Build message with details
        messages = []
        for item in items[:5]:  # Show up to 5 items
            if app_type == 'client':
                messages.append(f"• {item['name']} (ID: {item['id']})")
            elif app_type == 'invoice':
                messages.append(f"• {item['name']}: ${item['amount']:.2f}")
            elif app_type == 'content':
                messages.append(f"• {item['name']} ({item['platform']})")
        
        if count > 5:
            messages.append(f"... and {count - 5} more")
        
        message = "\n".join(messages)
        send_desktop_notification(title, message)
        
        print(f"Notified: {title}")
    
    # Also check for agent approvals
    check_agent_approvals()

def check_agent_approvals():
    """Check for pending agent approvals in agent files"""
    agents_dir = OMNI_SOURCE / "agents"
    
    if not agents_dir.exists():
        return
    
    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        
        approvals_file = agent_dir / "approvals.json"
        if approvals_file.exists():
            try:
                with open(approvals_file, 'r') as f:
                    approvals = json.load(f)
                
                pending = [a for a in approvals if a.get('status') == 'pending']
                
                if pending:
                    title = f"Agent {agent_dir.name} - {len(pending)} Pending Approval(s)"
                    messages = [f"• {a.get('description', 'Unknown')}" for a in pending[:3]]
                    message = "\n".join(messages)
                    send_desktop_notification(title, message)
                    print(f"Notified: {title}")
            except Exception as e:
                print(f"Error checking {agent_dir.name} approvals: {e}")

if __name__ == "__main__":
    check_and_notify()
