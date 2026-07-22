import sys
import os
from datetime import datetime

if len(sys.argv) < 4:
    print("Usage: python3 invoice.py [ArtistName] [Room A or B] [Hours]")
    sys.exit(1)

artist = sys.argv[1]
room = sys.argv[2].upper()
hours = float(sys.argv[3])

rate = 90 if "A" in room else 75
subtotal = hours * rate
deposit = subtotal * 50

invoice_text = f"""
==================================================
             VOLT RECORDS ATLANTA                 
            BOOKING CONFIRMATION                  
==================================================
DATE: {datetime.now().strftime('%Y-%m-%d')}
CLIENT: {artist}
SESSION TARGET: {room} Room Lockout
DURATION: {hours} Hours (@ ${rate}/hr)
--------------------------------------------------
TOTAL TIME COST:  ${subtotal:,.2f}
REQUiRED DEPOSIT: ${deposit:,.2f} (50% to lock dates)
--------------------------------------------------
PORTFOLIO BENCHMARK: http://sqtheafterparty.base44.app/

TO SECURE SEATS: Reply with your preferred payment 
method (CashApp, Apple Pay, or Zelle) to dispatch 
the secure processing link. Welcome to the roster.
==================================================
"""

output_path = os.path.expanduser(f"~/Omni-Studio/{artist}_invoice_draft.txt")
with open(output_path, "w") as f:
    f.write(invoice_text.strip())

print(invoice_text)
print(f"📄 Invoice draft securely saved to ~/Omni-Studio/{artist}_invoice_draft.txt")
