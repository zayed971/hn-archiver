"""HN Front Page Scraper — appends current front page to hn_archive.csv.

Uses the official Firebase HN API (free, no auth required).

Categories are heuristically assigned based on title keywords.
"""
import csv
import os
import re
import sys
from datetime import datetime

import requests

API_BASE = "https://hacker-news.firebaseio.com/v0"
TOP_STORIES = f"{API_BASE}/topstories.json"
ITEM = f"{API_BASE}/item/{{}}.json"
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hn_archive.csv")

# ---- Categorization ----
CATEGORY_RULES = [
    (r"\b(ai|artificial intelligence|machine learning|llm|gpt|claude|chatgpt|copilot|openai|anthropic|deepseek|midjourney|stable diffusion|transformer|neural|nlp|agent|rag|langchain)\b", "AI/ML"),
    (r"\b(rust|python|javascript|typescript|go|golang|java|sql|compiler|programming|framework|library|api|sdk|open source|github|git)\b", "Programming"),
    (r"\b(apple|google|microsoft|meta|facebook|amazon|tesla|netflix|nvidia|intel)\b", "Big Tech"),
    (r"\b(security|hack|vulnerability|exploit|cve|zero.day|breach|ransomware|malware|privacy)\b", "Security"),
    (r"\b(startup|yc|y.combinator|funding|series.\s?[abc]|seed|raised|\$\d+[mM]|valuation|ipo|acquisition|acquired)\b", "Startups"),
]


def categorize(title: str) -> str:
    t = title.lower()
    for pattern, cat in CATEGORY_RULES:
        if re.search(pattern, t):
            return cat
    return "Other"


def scrape():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get top story IDs
    resp = requests.get(TOP_STORIES, timeout=15)
    resp.raise_for_status()
    ids = resp.json()[:30]  # top 30

    # Check which IDs we already have
    existing = set()
    total_rows = 0
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                total_rows += 1
                hid = (row.get("hn_id") or "").strip()
                if hid:
                    existing.add(hid)
    except FileNotFoundError:
        pass

    # Defensive: this should never happen (existing already blocks re-adding a
    # seen hn_id), but if the archive was ever touched by another process/script
    # version, surface it loudly instead of silently accumulating more dupes.
    if total_rows != len(existing):
        print(
            f"WARNING: hn_archive.csv has {total_rows - len(existing)} duplicate hn_id rows. "
            "Dedupe before trusting counts from this file."
        )

    # Fetch each story, append new ones
    new_count = 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if os.path.getsize(CSV_PATH) == 0:
            writer.writerow(["timestamp", "rank", "title", "url", "points", "comments", "category", "hn_id"])

        for rank, hid in enumerate(ids, 1):
            if str(hid) in existing:
                continue
            try:
                item = requests.get(ITEM.format(hid), timeout=10).json()
                if item is None or item.get("type") != "story":
                    continue
                title = item.get("title", "")
                url = item.get("url", f"https://news.ycombinator.com/item?id={hid}")
                points = item.get("score", 0)
                comments = item.get("descendants", 0)
                cat = categorize(title)
                writer.writerow([now, rank, title, url, points, comments, cat, hid])
                new_count += 1
            except Exception:
                continue

    print(f"[{now}] Scraped {new_count} new stories (top 30 checked, {len(existing)} already archived)")
    return new_count


if __name__ == "__main__":
    scrape()
