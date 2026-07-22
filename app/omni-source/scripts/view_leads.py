import csv
import os
import sqlite3
from datetime import datetime


STATUS_ICONS = {
    'SCRAPED': '🔍',
    'PITCHED': '📧',
    'MUSIC_LIBRARY_TARGET': '🎵',
    'PENDING VERIFICATION': '⏳',
    'CLOSED': '💰',
    'CONTACTED': '📧',
    'RESPONDED': '💬',
    'CONVERTED': '✅',
    'REJECTED': '❌',
}


def show_music_library_dashboard(cursor):
    print("\n" + "=" * 80)
    print(" 🎵 MUSIC LIBRARY TARGETS DASHBOARD")
    print("=" * 80)

    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT sub_library) as libraries,
               AVG(CASE WHEN last_updated IS NOT NULL THEN 1.0 ELSE NULL END),
               MAX(created_at) as last_added
        FROM leads
        WHERE source = 'MUSIC_LIBRARY_TARGET'
    """)
    stats = cursor.fetchone()
    print(f"\n📊 OVERALL STATS:")
    print(f"   Total Targets: {stats[0]}")
    print(f"   Libraries Covered: {stats[1]}")
    print(f"   Last Added: {stats[3]}" if stats[3] else "   Last Added: N/A")

    cursor.execute("""
        SELECT sub_library, COUNT(*) as count, MAX(last_updated) as last_update
        FROM leads
        WHERE source = 'MUSIC_LIBRARY_TARGET'
        GROUP BY sub_library
        ORDER BY count DESC
    """)
    libraries = cursor.fetchall()

    if libraries:
        print(f"\n📚 BY SUB-LIBRARY:")
        print(f"{'LIBRARY':<20} | {'COUNT':<6} | LAST UPDATE")
        print("-" * 50)
        for row in libraries:
            print(f"{str(row[0]):<20} | {row[1]:<6} | {row[2]}")

    cursor.execute("""
        SELECT name, title, sub_library, linkedin_url
        FROM leads
        WHERE source = 'MUSIC_LIBRARY_TARGET'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    recent = cursor.fetchall()

    if recent:
        print(f"\n🆕 RECENT ADDITIONS:")
        print(f"{'NAME':<20} | {'TITLE':<25} | {'LIBRARY':<15} | LINKEDIN")
        print("-" * 90)
        for row in recent:
            name = str(row[0])[:20] if row[0] else "?"
            title = str(row[1])[:25] if row[1] else "?"
            sub = str(row[2])[:15] if row[2] else "?"
            print(f"{name:<20} | {title:<25} | {sub:<15} | {row[3]}")

    print("=" * 80 + "\n")


def export_music_targets(cursor, fmt='csv'):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.expanduser(f'~/Omni-Studio/exports/music_library_targets_{timestamp}.csv')
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    cursor.execute("""
        SELECT name, title, sub_library, linkedin_url, created_at
        FROM leads
        WHERE source = 'MUSIC_LIBRARY_TARGET'
        ORDER BY sub_library, name
    """)

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Title', 'Sub-Library', 'LinkedIn URL', 'Added'])
        writer.writerows(cursor.fetchall())

    print(f"\n📁 Exported to: {filepath}")
    return filepath


def view_leads():
    db_path = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')

    if not os.path.exists(db_path):
        print("⚠️  No database found. Run your scraper first!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM leads")
        true_total = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
        breakdown = cursor.fetchall()

        cursor.execute("SELECT id, name, email, city, status FROM leads ORDER BY id DESC LIMIT 900")
        leads = cursor.fetchall()

        print("\n" + "=" * 89)
        print(f" 🎯 VOLT RECORDS | COMMAND CENTER LEADS (TRUE TOTAL: {true_total})")
        print("=" * 89)
        print(" 📊 SOURCE BREAKDOWN:")

        for status, count in breakdown:
            icon = STATUS_ICONS.get(status, '⚙️')
            if status in ['SCRAPED', 'PITCHED']:
                source = "🤖 Web Scraper"
            elif status == 'PENDING VERIFICATION':
                source = "📧 Email Auditor (Missed Funds)"
            elif status == 'CLOSED':
                source = "💰 Paid / Locked"
            elif status == 'MUSIC_LIBRARY_TARGET':
                source = "🎵 Music Library Aggregator"
            else:
                source = "⚙️ System"
            print(f"    - {status:<22}: {count:<5} | {icon} {source}")

        print("-" * 89)
        print(f"{'ID':<5} | {'NAME':<20} | {'EMAIL':<30} | {'CITY':<12} | {'STATUS'}")
        print("-" * 89)

        if not leads:
            print(" 👻 No leads in the database yet.")
        else:
            for lead in leads:
                name = str(lead[1])[:20] if lead[1] else "Unknown"
                email = str(lead[2])[:30] if lead[2] else "Unknown"
                city = str(lead[3]).title()[:12] if lead[3] else "Unknown"
                status = str(lead[4])
                print(f"{lead[0]:<5} | {name:<20} | {email:<30} | {city:<12} | {status}")

        print("-" * 89)
        print(f" 🔥 TOTAL LEADS SECURED IN DATABASE: {true_total}")
        print("=" * 89 + "\n")

        cursor.execute("SELECT COUNT(*) FROM leads WHERE source = 'MUSIC_LIBRARY_TARGET'")
        music_count = cursor.fetchone()[0]
        if music_count > 0:
            show_music_library_dashboard(cursor)

    except sqlite3.OperationalError:
        print("⚠️  Table 'leads' doesn't exist yet. Run the scraper or migrate_music_library_schema.py first.")
    except Exception as e:
        print(f"🛑 Error reading database: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    view_leads()

