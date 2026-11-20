"""
Shared reader for WordPress "opportunity" blogs (Opportunities For Youth,
Opportunity Desk). Not a source itself: ofy.py and opportunitydesk.py use it.

These blogs post everything from journalism fellowships to MBA scholarships,
so a post is only kept when:
  1. its title isn't clearly a job / PhD / postdoc / grant / advice post,
  2. it matches one of your field keywords (ML/AI alone isn't enough, since
     "AI" appears in many policy and business posts), and
  3. its title (or category) tells us which type it is.
"""

import re
from datetime import date, timedelta

import feedparser
import requests

from helpers import (fetch, find_deadline_in_text, guess_type, html_to_text,
                     make_item, match_fields, to_date, today)

# WordPress category name (lower-case) -> our type, used when the title alone
# doesn't say.
CATEGORY_TYPES = {
    "internships": "internship", "fellowships": "fellowship", "scholarships": "fellowship",
    "conferences": "conference", "summer schools": "summer-school", "competitions": "competition",
    "workshops": "workshop", "training": "workshop",
}
SKIP_TITLE_RX = re.compile(
    r"\bph\.?d\b|post-?doc|post-doctoral|\bjobs?\b|vacanc|\bpositions?\b|\bgrants?\b|\bmba\b"
    r"|master'?s|tips|how to|currently open|^\d+\s",   # "20 Scholarships ... Currently Open" roundups
    re.I,
)
MAX_AGE_WITHOUT_DEADLINE = 90       # days: older posts with no stated deadline are skipped
TEXT_WINDOW = 1500                  # these posts open with generic intros, so read further


def _stipend(title):
    t = title.lower()
    if "fully funded" in t or "fully-funded" in t:
        return "Fully funded"
    if "funded" in t:
        return "Funded"
    if re.search(r"\bpaid\b|stipend", t):
        return "Paid"
    return ""


def read_feed(source, site_name, feed_url, pages):
    """Read up to `pages` pages (10 posts each) of a WordPress feed."""
    items = []
    oldest = today() - timedelta(days=MAX_AGE_WITHOUT_DEADLINE)
    for page in range(1, pages + 1):
        url = feed_url if page == 1 else f"{feed_url}?paged={page}"
        try:
            feed = feedparser.parse(fetch(url, kind="bytes"))
        except requests.HTTPError:
            break                               # WordPress answers 404 after the last page
        if not feed.entries:
            break

        for entry in feed.entries:
            title = entry.get("title") or ""
            if SKIP_TITLE_RX.search(title):
                continue
            content = entry.get("content", [{}])[0].get("value") or entry.get("summary", "")
            text = html_to_text(content)
            fields = match_fields(f"{title} {text[:TEXT_WINDOW]}")
            science = [f for f in fields if f != "ml-ai"]
            if not science:
                continue                        # not science-related
            if science == ["healthcare-ai"] and not re.search(r"scien|research|medic|bio|clinic|pharma", title, re.I):
                continue                        # only "health" mentioned, e.g. a youth-policy forum

            categories = [t.get("term", "").lower() for t in entry.get("tags", [])]
            hint = next((CATEGORY_TYPES[c] for c in categories if c in CATEGORY_TYPES), "")
            online = bool(re.search(r"\bonline\b|\bvirtual\b|\bremote\b", title, re.I))
            kind = guess_type(title, hint, online=online)
            if not kind:
                continue                        # can't tell what it is

            deadline = find_deadline_in_text(text)
            posted = to_date(entry.get("published_parsed"))
            if not deadline and posted and date.fromisoformat(posted) < oldest:
                continue                        # old post, probably closed

            item = make_item(
                source=source,
                title=title,
                type=kind,
                mode="online" if online else "offline",
                location="Online" if online else "",
                deadline=deadline,
                stipend_or_prize=_stipend(title),
                notes=f"Posted {posted} on {site_name}" if posted else "",
                url=entry.get("link"),
                fields=fields,                  # already matched on the longer text above
            )
            if item:
                items.append(item)
    return items
