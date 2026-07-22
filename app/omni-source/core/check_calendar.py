import json
import os
import sys
from datetime import datetime

CALENDAR_PATH = os.path.expanduser("~/Omni-Studio/studio_calendar.json")

def check_booking(room, date_str, start_str, duration_hours):
    if not os.path.exists(CALENDAR_PATH):
        return True, "No calendar found. Slot is open."
        
    with open(CALENDAR_PATH, "r") as f:
        calendar = json.load(f)
        
    room_key = "A_Room" if "A" in room.upper() else "B_Room"
    bookings = calendar.get(room_key, [])
    
    # Parse target times
    fmt = "%H:%M"
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    target_start = datetime.strptime(start_str, fmt).time()
    
    # Calculate target end time
    start_dt = datetime.combine(target_date, target_start)
    end_dt = start_dt + timedelta(hours=float(duration_hours))
    target_end = end_dt.time()
    
    for b in bookings:
        if b["date"] == date_str:
            b_start = datetime.strptime(b["start"], fmt).time()
            b_end = datetime.strptime(b["end"], fmt).time()
            
            # Check for overlapping schedules
            if not (target_end <= b_start or target_start >= b_end):
                return False, f"Conflict: Blocked by {b['artist']} ({b['start']}-{b['end']})"
                
    return True, "Available!"

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 check_calendar.py [Room A/B] [YYYY-MM-DD] [HH:MM] [DurationHours]")
        sys.exit(1)
        
    from datetime import timedelta
    available, msg = check_booking(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print(json.dumps({"available": available, "message": msg}))
