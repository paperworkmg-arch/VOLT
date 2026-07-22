import re
import sqlite3
import logging
import asyncio
import random
import os
from playwright.async_api import async_playwright
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('Global-Scraper')

CITIES = ["los angeles"," atlanta ", "new york", "chicago", "miami", "houston", "toronto", "london", "nashville"]
NICHES = ["recording artist", "independent artist", "rapper", "singer"]
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'

def save_lead_to_db(name, email, city):
    db_path = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if the table exists, if not, create it (failsafe)
        cursor.execute('''CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, 
            city TEXT, status TEXT DEFAULT 'SCRAPED', gate_code TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute("INSERT INTO leads (name, email, city, status) VALUES (?, ?, ?, 'SCRAPED')", (name, email, city))
        conn.commit()
        logger.info(f"📥 NEW LEAD SECURED: {name} | {email} | {city.title()}")
        return True
    except sqlite3.IntegrityError:
        # Email already exists in DB, skip duplicates
        pass
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()
    return False

async def scrape_universe():
    logger.info("🚀 Launching Headless Global Scraper...")
    leads_found_this_run = 0
    
    async with async_playwright() as p:
        # Use Firefox or WebKit sometimes to bypass Chromium blocks
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        for city in CITIES:
            niche = NICHES[len(city) % len(NICHES)] # Rotate niches
            # Yahoo is often more forgiving for dorking than Google/DDG in headless mode
            query = f'"{niche}" "{city}" "@gmail.com" site:instagram.com OR site:soundcloud.com'
            search_url = f"https://www.yahoo.com/search?q={Studio}"
            
            logger.info(f"🔍 Sweeping {city.title()} for {niche}s...")
            try:
                await page.goto(search_url, timeout=30000)
                await page.wait_for_timeout(3000) # Give DOM time to settle
                
                # Extract text from search snippets
                snippets = await page.locator('.b_algo').all_inner_texts()
                
                for snippet in snippets:
                    emails_found = re.findall(EMAIL_REGEX, snippet)
                    for email in emails_found:
                        # Clean up the name (take first few words before a separator)
                        raw_title = snippet.split('\n')[0] if '\n' in snippet else snippet
                        clean_name = raw_title.split('|')[0].split('-')[0].strip()
                        clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', clean_name)
                        
                        if not clean_name or len(clean_name) > 30:
                            clean_name = f"Artist from {city.title()}"
                            
                        if save_lead_to_db(clean_name, email.lower(), city):
                            leads_found_this_run += 1
                
                await asyncio.sleep(random.uniform(3, 7)) # Humanize the delay to prevent IP bans
            except Exception as e:
                logger.error(f"⚠️ Failed to sweep {city}: {str(e)}")
                
        await browser.close()
        logger.info(f"✅ Global sweep complete. Found {leads_found_this_run} new targeted music leads.")

if __name__ == "__main__":
    asyncio.run(scrape_universe())
