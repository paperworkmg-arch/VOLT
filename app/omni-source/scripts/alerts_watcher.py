#!/usr/bin/env python3
import os
import re
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime
from html import unescape

BASE = Path.home() / "Omni-Studio"
LEADS_DIR = BASE / "Incoming_Leads"
SEEN_FILE = BASE / "data" / "alerts_seen.json"
LOG_FILE = BASE / "alerts_watcher.log"
FEEDS_FILE = BASE / "data" / "alert_feeds.txt"

CHECK_INTERVAL_SECONDS = 900

LEADS_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    line = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + msg
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_feeds():
    if FEEDS_FILE.exists():
        return [line.strip() for line in FEEDS_FILE.read_text().splitlines() if line.strip()]
    return []


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def strip_html(text):
    # Unwrap CDATA, unescape entities so &lt;b&gt; becomes real tags, strip, unescape again
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def fetch_feed(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; StudioAlertsReader/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_entries(xml_text):
    parsed = []
    # Atom feeds (Google Alerts)
    for entry in re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL):
        title_match = re.search(r"<title[^>]*>(.*?)</title>", entry, re.DOTALL)
        link_match = re.search(r"<link[^>]*href=\"([^\"]*)\"", entry)
        summary_match = re.search(r"<content[^>]*>(.*?)</content>", entry, re.DOTALL)
        id_match = re.search(r"<id>(.*?)</id>", entry, re.DOTALL)

        if not (title_match and link_match):
            continue

        parsed.append({
            "title": strip_html(title_match.group(1)),
            "link": link_match.group(1),
            "summary": strip_html(summary_match.group(1)) if summary_match else "",
            "id": id_match.group(1).strip() if id_match else link_match.group(1),
        })
    # RSS 2.0 feeds (music blogs, Google News)
    for item in re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL):
        title_match = re.search(r"<title[^>]*>(.*?)</title>", item, re.DOTALL)
        link_match = re.search(r"<link[^>]*>(.*?)</link>", item, re.DOTALL)
        desc_match = re.search(r"<description[^>]*>(.*?)</description>", item, re.DOTALL)
        guid_match = re.search(r"<guid[^>]*>(.*?)</guid>", item, re.DOTALL)

        if not (title_match and link_match):
            continue

        link = strip_html(link_match.group(1))
        parsed.append({
            "title": strip_html(title_match.group(1)),
            "link": link,
            "summary": strip_html(desc_match.group(1)) if desc_match else "",
            "id": strip_html(guid_match.group(1)) if guid_match else link,
        })
    return parsed


def write_lead(entry, source_feed):
    clean_name = re.sub(r"[^a-zA-Z0-9]", "", entry["title"].split()[0])[:15] or "Lead"
    filename = clean_name + "_" + str(int(time.time())) + ".txt"
    path = LEADS_DIR / filename

    text = "Source: Feed (" + source_feed + ")\n"
    text += "Title: " + entry["title"] + "\n"
    text += "Message: \"" + (entry["summary"] or entry["title"]) + "\"\n"
    text += "Contact: " + entry["link"] + "\n"
    path.write_text(text)
    log("  New lead captured: " + entry["title"][:60])


def run_once(seen, feeds):
    if not feeds:
        log("No feeds configured yet - check alert_feeds.txt.")
        return seen

    for feed_url in feeds:
        try:
            xml_text = fetch_feed(feed_url)
            entries = parse_entries(xml_text)
        except Exception as e:
            log("Error fetching feed " + feed_url[:60] + "...: " + str(e))
            continue

        new_count = 0
        for entry in entries:
            if entry["id"] not in seen:
                write_lead(entry, feed_url[-20:])
                seen.add(entry["id"])
                new_count += 1

        log("Checked feed ..." + feed_url[-20:] + ": " + str(new_count) + " new / " + str(len(entries)) + " total entries")

    save_seen(seen)
    return seen


def main():
    log("Google Alerts watcher online.")
    seen = load_seen()
    while True:
        feeds = load_feeds()
        seen = run_once(seen, feeds)
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
