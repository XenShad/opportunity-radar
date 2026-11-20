"""
Opportunity Desk - international internships, fellowships and training
programmes (all fields; we keep science ones).

How: the site's WordPress category RSS feeds (config.OPPORTUNITYDESK_FEEDS).
Its terms of service have no rule against reading the feeds. Filtering lives
in sources/opportunity_feeds.py.
"""

import config
from sources.opportunity_feeds import read_feed

NAME = "opportunitydesk"


def fetch_items():
    items = []
    for slug, pages in config.OPPORTUNITYDESK_FEEDS.items():
        items += read_feed(NAME, "Opportunity Desk", f"https://opportunitydesk.org/category/{slug}/feed/", pages)
    return items
