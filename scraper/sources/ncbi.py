"""
NCBI Insights - the official blog of the US National Center for
Biotechnology Information (GenBank, BLAST, PubMed...). NCBI announces its
webinars, codeathons and virtual workshops here.

How: the blog's WordPress RSS feed (its REST API needs a login; the feed
doesn't). Only posts whose title matches config.NCBI_TITLE_PATTERN are kept,
and only if the post mentions a date that is still in the future, so old
announcements of past webinars don't sneak in.
"""

import re

import feedparser

import config
from helpers import (fetch, find_deadline_in_text, find_event_date_in_text,
                     guess_type, html_to_text, make_item, to_date)

NAME = "ncbi"
FEED = "https://ncbiinsights.ncbi.nlm.nih.gov/feed/"


def fetch_items():
    feed = feedparser.parse(fetch(FEED, kind="bytes"))
    items = []
    for entry in feed.entries:
        title = entry.get("title") or ""
        if not re.search(config.NCBI_TITLE_PATTERN, title, re.I):
            continue                            # ordinary news post

        content = entry.get("content", [{}])[0].get("value") or entry.get("summary", "")
        text = html_to_text(content)
        # A registration deadline if the post states one, else the first
        # future date in the post (for a webinar, that's the webinar itself).
        date = find_deadline_in_text(text) or find_event_date_in_text(text)
        if not date:
            continue                            # nothing upcoming in this post

        if re.search(r"\bhybrid\b", text, re.I):
            mode = "hybrid"
        elif re.search(r"\bin[- ]person\b|\bon[- ]site\b", text, re.I):
            mode = "offline"
        else:
            mode = "online"                     # most NCBI events are virtual

        posted = to_date(entry.get("published_parsed"))
        item = make_item(
            source=NAME,
            title=title,
            organiser="NCBI (US National Library of Medicine)",
            type=guess_type(title, "webinar", online=mode == "online"),
            mode=mode,
            location="Online" if mode == "online" else "",
            deadline=date,
            notes=f"Announced {posted} on NCBI Insights" if posted else "",
            url=entry.get("link"),
            tag_text=f"bioinformatics {text[:1500]}",
            bio_source=True,
        )
        if item:
            items.append(item)
    return items
