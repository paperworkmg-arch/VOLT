#!/usr/bin/env python3
"""
Approval Manager - CLI interface for managing approvals
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Paths
OMNI_SOURCE = Path(__file__).parent.parent
DATA_DIR = OMNI_SOURCE / "data"
CRM_DB = DATA_DIR / "business" / "crm.db"

def list_approvals():
    """List all pending approvals"""
    if not CRM_DB.exists():
        print("CRM database not found")
        return
    
    conn = sqlite3.connect(str(CRM_DB))
    cursor = conn.cursor()
    
    print("\n=== Pending Approvals ===\n")
    
    # Clients
    cursor.execute("SELECT id, client_name, notes, created_at FROM clients WHERE status = 'pending_approval'")
    clients = cursor.fetchall()
    if clients:
        print("CLIENTS:")
        for row in clients:
            print(f"  [{row[0]}] {row[1]} - {row[2] or 'No notes'} (Created: {row[3]})")
    
    # Invoices
    cursor.execute("SELECT id, client_name, amount, created_at FROM invoices WHERE status = 'pending_approval'")
    invoices = cursor.fetchall()
    if invoices:
        print("\nINVOICES:")
        for row in invoices:
            print(f"  [{row[0]}] {row[1]}: ${row[2]:.2f} (Created: {row[3]})")
    
    # Content
    cursor.execute("SELECT id, title, platform, created_at FROM content WHERE status = 'pending_approval'")
    content = cursor.fetchall()
    if content:
        print("\nCONTENT:")
        for row in content:
            print(f"  [{row[0]}] {row[1]} ({row[2]}) (Created: {row[3]})")
    
    if not clients and not invoices and not content:
        print("No pending approvals found.")
    
    conn.close()

def approve_item(item_type, item_id):
    """Approve an item"""
    if not CRM_DB.exists():
        print("CRM database not found")
        return
    
    conn = sqlite3.connect(str(CRM_DB))
    cursor = conn.cursor()
    
    table_map = {
        'client': 'clients',
        'invoice': 'invoices',
        'content': 'content'
    }
    
    table = table_map.get(item_type)
    if not table:
        print(f"Unknown item type: {item_type}")
        return
    
    cursor.execute(f"UPDATE {table} SET status = 'approved' WHERE id = ?", (item_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        print(f"Approved {item_type} {item_id}")
    else:
        print(f"Could not find {item_type} {item_id}")
    
    conn.close()

def reject_item(item_type, item_id):
    """Reject an item"""
    if not CRM_DB.exists():
        print("CRM database not found")
        return
    
    conn = sqlite3.connect(str(CRM_DB))
    cursor = conn.cursor()
    
    table_map = {
        'client': 'clients',
        'invoice': 'invoices',
        'content': 'content'
    }
    
    table = table_map.get(item_type)
    if not table:
        print(f"Unknown item type: {item_type}")
        return
    
    cursor.execute(f"UPDATE {table} SET status = 'rejected' WHERE id = ?", (item_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        print(f"Rejected {item_type} {item_id}")
    else:
        print(f"Could not find {item_type} {item_id}")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python approval_manager.py [list|approve|reject] [type] [id]")
        print("  list - List all pending approvals")
        print("  approve [type] [id] - Approve an item (client/invoice/content)")
        print("  reject [type] [id] - Reject an item (client/invoice/content)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_approvals()
    elif command in ["approve", "reject"]:
        if len(sys.argv) < 4:
            print(f"Usage: python approval_manager.py {command} [type] [id]")
            sys.exit(1)
        
        item_type = sys.argv[2]
        item_id = sys.argv[3]
        
        if command == "approve":
            approve_item(item_type, item_id)
        else:
            reject_item(item_type, item_id)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
