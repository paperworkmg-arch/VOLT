import re
import sqlite3
import logging
import asyncio
import random
import os
from playwright.async_api import async_playwright
from datetime import datetime

from local_llm_connector import query_local_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('Volt-Scraper')

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

CITIES = [
    "Atlanta", "Houston", "Miami", "Los Angeles", "Chicago",
    "Dallas", "Nashville", "Memphis", "New Orleans", "Charlotte",
    "Phoenix", "Detroit", "Oakland", "Philadelphia", "New York"
]

NICHES = [
    "music producer", "recording artist", "rapper", "singer",
    "beatmaker", "audio engineer", "songwriter", "DJ",
    "music manager", "label owner"
]

def generate_custom_hook(city, niche, snippet):
    try:
        system_prompt = "You are a ruthless, high-end music executive. Write a ONE SENTENCE cold email opening hook for an artist based on the provided web search snippet. Make it sound like you personally listened to their track and see potential. Be edgy. No hashtags."
        user_message = f"City: {city}, Niche: {niche}, Web Snippet: {snippet}"
        result = query_local_llm(f"{system_prompt}\n\n{user_message}")
        if result and not result.startswith("Error:"):
            return result.strip()
        else:
            return f"Word around {city.title()} is you're making noise."
    except Exception as e:
        logger.error(f"Hook generation failed: {e}")
        return f"Word around {city.title()} is you're making noise."

def save_lead_to_db(name, email, city, hook):
    db_path = os.path.expanduser('~/Omni-Studio/data/studio_crm.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
            city TEXT, status TEXT DEFAULT 'SCRAPED', gate_code TEXT, custom_hook TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN custom_hook TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("INSERT INTO leads (name, email, city, status, custom_hook) VALUES (?, ?, ?, 'SCRAPED', ?)", (name, email, city, hook))
        conn.commit()
        logger.info(f"NEW LEAD SECURED: {name} | {email} | {city.title()}")
        return True
    except sqlite3.IntegrityError:
        pass
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()
    return False

async def scrape_universe():
    logger.info("Launching Headless Global Scraper...")
    leads_found_this_run = 0

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        for city in CITIES:
            niche = NICHES[len(city) % len(NICHES)]
            query = f'"{niche}" "{city}" "@gmail.com" site:instagram.com OR site:soundcloud.com'
            search_url = f"https://www.bing.com/search?q={query}"

            logger.info(f"Sweeping {city.title()} for {niche}s...")
            try:
                await page.goto(search_url, timeout=20000)
                await page.wait_for_timeout(2000)

                snippets = await page.locator('.b_algo').all_inner_texts()

                for snippet in snippets:
                    emails_found = re.findall(EMAIL_REGEX, snippet)
                    for email in emails_found:
                        raw_title = snippet.split('\n')[0] if '\n' in snippet else snippet
                        clean_name = raw_title.split('|')[0].split('-')[0].strip()
                        clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', clean_name)

                        if not clean_name or len(clean_name) > 30:
                            clean_name = f"Artist from {city.title()}"

                        logger.info(f"Generating custom hook for {clean_name}...")
                        custom_hook = generate_custom_hook(city, niche, snippet)

                        if save_lead_to_db(clean_name, email.lower(), city, custom_hook):
                            leads_found_this_run += 1

                await asyncio.sleep(random.uniform(3, 7))
            except Exception as e:
                logger.error(f"Failed to sweep {city}: {str(e)}")

        await browser.close()
        logger.info(f"Global sweep complete. Found {leads_found_this_run} new targeted music leads.")

if __name__ == "__main__":
    asyncio.run(scrape_universe())
