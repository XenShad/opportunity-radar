"""
Galaxy Project events - workshops, webinars, hackathons and conferences
around Galaxy, the open web platform for bioinformatics analysis.

How: the public events RSS feed (https://galaxyproject.org/events/feed.xml).
Galaxy puts each event's START DATE in the item's publish date, so we keep
only items dated today or later. The feed has no location field; the mode
(online / hybrid / in person) is guessed from the title and summary.
"""

import re

import feedparser

import config
from helpers import fetch, guess_type, html_to_text, make_item, to_date, today

NAME = "galaxy"
FEED = "https://galaxyproject.org/events/feed.xml"


def guess_mode(text):
    """'a one-day hybrid sprint' -> hybrid, 'online webinar' -> online, else offline."""
    if re.search(r"\bhybrid\b", text, re.I):
        return "hybrid"
    if re.search(r"\bon-?site\b|\bin[- ]person\b", text, re.I):
        return "offline"                     # "on-site course (preceded by webinars)"
    if re.search(r"\bonline\b|\bvirtual\b|\bwebinars?\b|\bzoom\b|\bremote\b|\blivestream", text, re.I):
        return "online"
    return "offline"


def fetch_items():
    feed = feedparser.parse(fetch(FEED, kind="bytes"))
    items = []
    for entry in feed.entries:
        start = to_date(entry.get("published_parsed"))      # = the event date here
        if not start or start < today().isoformat():
            continue                                         # past event

        title = entry.get("title") or ""
        summary = html_to_text(entry.get("summary") or "")
        if re.search(config.GALAXY_SKIP_PATTERN, f"{title} {summary}", re.I):
            continue                         # Galaxy also serves non-bio communities
        mode = guess_mode(f"{title} {summary}")
        online = mode == "online"
        # Title first; if it says nothing about the type, try the summary.
        kind = guess_type(title, default="", online=online) or guess_type(summary, "workshop", online=online)
        if kind == "webinar" and not online:
            kind = "workshop"                # an in-person event that merely mentions webinars

        item = make_item(
            source=NAME,
            title=title,
            organiser="Galaxy Project community",
            type=kind,
            mode=mode,
            location="Online" if online else "",
            start_date=start,
            deadline=start,                  # register before it starts
            url=entry.get("link"),
            tag_text=f"bioinformatics {summary}",
            bio_source=True,
        )
        if item:
            items.append(item)
    return items
