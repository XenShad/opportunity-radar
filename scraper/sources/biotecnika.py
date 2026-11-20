"""
Biotecnika - Indian biotech/life-science internships, fellowships, workshops.

How: WordPress category RSS feeds (one per category in
config.BIOTECNIKA_FEEDS). Biotecnika posts rarely have structured dates, so we
look for phrases like "Last date: 30 November 2026" in the post text.

Heads-up: the site sits behind Cloudflare, which sometimes answers automated
requests with a "Just a moment..." bot check (HTTP 403). We respect that: on
the first block we stop asking (no retries, no workarounds) and update.py keeps
the items from the last successful run.
"""

import re
from datetime import date, timedelta

import feedparser

import config
from helpers import (SourceBlocked, fetch, find_deadline_in_text, find_india_place,
                     guess_type, html_to_text, make_item, to_date, today, warn)

NAME = "biotecnika"
FEED_URL = "https://www.biotecnika.org/category/{slug}/feed/"

# "Rs 15,000", "₹ 8000", "INR 12,000" (shortly after the word stipend/fellowship/salary)
_STIPEND_RX = re.compile(
    r"(?:stipend|fellowship amount|emoluments?|salary|honorarium)[^.₹]{0,40}"
    r"((?:rs\.?|inr|₹)\s?[\d,]+(?:\s?(?:/-|per month|pm|p\.m\.))?)",
    re.I,
)


def _mode_and_location(title):
    """Biotecnika titles often name the city: 'ICAR-NBAIR Bengaluru SRF ...'."""
    if re.search(r"\bonline\b|\bvirtual\b|\bwebinar\b", title, re.I):
        return "online", "Online"
    place = find_india_place(title)
    if place and place.lower() != "india":
        return "offline", f"{place}, India"
    return "offline", "India"


def fetch_items():
    oldest = today() - timedelta(days=config.BIOTECNIKA_MAX_AGE_DAYS)
    items, seen = [], set()

    for slug, default_type in config.BIOTECNIKA_FEEDS.items():
        try:
            feed = feedparser.parse(fetch(FEED_URL.format(slug=slug), kind="bytes"))
        except SourceBlocked as e:
            if not items:
                raise                           # blocked straight away: whole source is "blocked"
            warn(f"stopped at category '{slug}' ({e}); keeping {len(items)} items already read")
            break                               # don't keep knocking once the site says no

        for entry in feed.entries:
            link = entry.get("link")
            published = to_date(entry.get("published_parsed"))
            if not link or link in seen or (published and date.fromisoformat(published) < oldest):
                continue
            seen.add(link)

            title = entry.get("title") or ""
            content = entry.get("content", [{}])[0].get("value") or entry.get("summary", "")
            text = html_to_text(content)
            stipend = _STIPEND_RX.search(text)
            mode, location = _mode_and_location(title)
            item = make_item(
                source=NAME,
                title=title,
                organiser="",                   # not structured in the feed
                type=guess_type(title, default_type),
                mode=mode,
                location=location,
                deadline=find_deadline_in_text(text),
                stipend_or_prize=stipend.group(1) if stipend else "",
                notes=f"Posted {published} on Biotecnika" if published else "",
                url=link,
                tag_text=text[:2000],
                bio_source=True,
            )
            if item:
                items.append(item)
    return items
