"""
MLH (Major League Hacking) - student hackathons worldwide.

How: MLH's official API needs a login, but the public season page
(https://www.mlh.com/seasons/2027/events) embeds its event list as JSON inside
a <script data-page="app"> tag. Reading that JSON is far more reliable than
parsing the visible HTML. robots.txt allows /seasons/.
"""

import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from helpers import fetch, make_item, today

NAME = "mlh"

# MLH's "formatType" -> our "mode"
MODE_MAP = {"physical": "offline", "virtual": "online", "digital": "online", "hybrid": "hybrid"}


def season_year(day):
    """MLH seasons run roughly August -> July and are named after the ending year."""
    return day.year + 1 if day.month >= 8 else day.year


def fetch_items():
    url = f"https://www.mlh.com/seasons/{season_year(today())}/events"
    page = fetch(url, kind="text")

    script = BeautifulSoup(page, "html.parser").find("script", attrs={"data-page": "app"})
    if script is None or not script.string:
        raise RuntimeError("MLH page layout changed: <script data-page='app'> not found")
    events = json.loads(script.string)["props"].get("upcomingEvents", [])

    items = []
    for ev in events:
        mode = MODE_MAP.get(ev.get("formatType"), "offline")
        venue = ev.get("venueAddress") or {}
        location = ev.get("location") or ", ".join(
            part for part in (venue.get("city"), venue.get("country")) if part
        )
        focus = ", ".join((ev.get("customFields") or {}).get("hackathon_focus") or [])

        item = make_item(
            source=NAME,
            title=ev.get("name"),
            organiser=ev.get("organizationName") or "MLH member event",
            type="hackathon",
            mode=mode,
            location=location,
            start_date=ev.get("startsAt"),
            end_date=ev.get("endsAt"),
            # MLH doesn't publish a registration deadline; registration
            # closes by the time the event starts at the latest.
            deadline=ev.get("startsAt"),
            eligibility="Students (check the event site for age and school rules)",
            url=ev.get("websiteUrl") or urljoin("https://www.mlh.com", ev.get("url") or ""),
            tag_text=f"hackathon {focus}",
        )
        if item:
            items.append(item)
    return items
