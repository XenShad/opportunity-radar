"""
Opportunities For Youth - international internships, fellowships, summer
schools, conferences and competitions (all fields; we keep science ones).

How: the site's WordPress RSS feed, several pages deep (see
config.OFY_PAGES). Filtering lives in sources/opportunity_feeds.py.
"""

import config
from sources.opportunity_feeds import read_feed

NAME = "ofy"


def fetch_items():
    items = read_feed(NAME, "Opportunities For Youth", "https://opportunitiesforyouth.org/feed/", config.OFY_PAGES)
    # the conferences category often has extra science meetings
    items += read_feed(NAME, "Opportunities For Youth",
                       "https://opportunitiesforyouth.org/category/conferences/feed/", 1)
    return items
