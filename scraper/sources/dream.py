"""
DREAM Challenges - open biomedical data science challenges (single-cell,
drug discovery, Alzheimer's, ...), run with Sage Bionetworks on Synapse.

How: the site's WordPress RSS feed. Each challenge is a post; posts tagged
"Open Challenge" or "Pre-Register" are currently accepting participants.
"""

import feedparser

from helpers import fetch, find_deadline_in_text, html_to_text, make_item

NAME = "dream"
FEED = "https://dreamchallenges.org/feed/"
OPEN_CATEGORIES = {"open challenge", "pre-register"}


def fetch_items():
    feed = feedparser.parse(fetch(FEED, kind="bytes"))
    items = []
    for entry in feed.entries:
        categories = [tag.get("term", "") for tag in entry.get("tags", [])]
        if not OPEN_CATEGORIES & {c.lower() for c in categories}:
            continue                            # closed or just news

        content = entry.get("content", [{}])[0].get("value") or entry.get("summary", "")
        text = html_to_text(content)
        item = make_item(
            source=NAME,
            title=entry.get("title"),
            organiser="DREAM Challenges / Sage Bionetworks",
            type="competition",
            mode="online",
            deadline=find_deadline_in_text(text),
            eligibility="Open to anyone with a free Synapse account",
            notes="Pre-registration open" if "pre-register" in {c.lower() for c in categories} else "",
            url=entry.get("link"),
            tag_text=f"{' '.join(categories)} {text[:2000]}",
            bio_source=True,
        )
        if item:
            items.append(item)
    return items
