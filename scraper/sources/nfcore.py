"""
nf-core events - the community behind best-practice Nextflow bioinformatics
pipelines. Mostly "bytesize" talks (short weekly webinars), hackathons and
training sessions.

How: the public events RSS feed (https://nf-co.re/events/rss.xml).
Like Galaxy, each item's publish date is the event date. The feed goes back
to 2018, so only upcoming events are kept.
"""

import feedparser

from helpers import fetch, guess_type, html_to_text, make_item, to_date, today
from sources.galaxy import guess_mode

NAME = "nfcore"
FEED = "https://nf-co.re/events/rss.xml"


def fetch_items():
    feed = feedparser.parse(fetch(FEED, kind="bytes"))
    items = []
    for entry in feed.entries:
        start = to_date(entry.get("published_parsed"))
        if not start or start < today().isoformat():
            continue

        title = entry.get("title") or ""
        summary = html_to_text(entry.get("summary") or "")
        mode = guess_mode(f"{title} {summary}")
        if title.lower().startswith("bytesize"):
            mode = "online"                  # bytesize talks are always online
        online = mode == "online"
        kind = guess_type(title, default="", online=online) or guess_type(
            summary, "webinar" if online else "workshop", online=online)

        item = make_item(
            source=NAME,
            title=title,
            organiser="nf-core community",
            type=kind,
            mode=mode,
            location="Online" if online else "",
            start_date=start,
            deadline=start,
            eligibility="Open to everyone",
            url=entry.get("link"),
            tag_text=f"bioinformatics nextflow pipelines {summary}",
            bio_source=True,
        )
        if item:
            items.append(item)
    return items
