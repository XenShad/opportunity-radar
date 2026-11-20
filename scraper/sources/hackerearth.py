"""
HackerEarth - online hackathons and hiring challenges.

How: a small public JSON endpoint HackerEarth provides for its browser
extension. It usually lists only a handful of current challenges.
"""

from helpers import fetch, html_to_text, make_item

NAME = "hackerearth"
URL = "https://www.hackerearth.com/chrome-extension/events/"


def fetch_items():
    data = fetch(URL)
    items = []
    for ev in data.get("response", []):
        url = ev.get("url") or ""
        kind = "hackathon" if "/hackathon/" in url else "competition"
        item = make_item(
            source=NAME,
            title=ev.get("title"),
            organiser="HackerEarth" if ev.get("is_hackerearth") else "",
            type=kind,
            mode="online",
            start_date=ev.get("start_tz"),
            end_date=ev.get("end_tz"),
            deadline=ev.get("end_tz"),          # you can join until it ends
            eligibility="College students only" if ev.get("college") else "",
            url=url,
            tag_text=html_to_text(ev.get("description") or ""),
        )
        if item:
            items.append(item)
    return items
