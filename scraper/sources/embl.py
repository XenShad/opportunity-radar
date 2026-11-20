"""
EMBL events - courses, conferences (including EMBO Workshops) and webinars
run by the European Molecular Biology Laboratory at Heidelberg, EMBL-EBI
(Hinxton, UK), Barcelona, Rome, Hamburg and Grenoble, plus virtual ones.

How: the public events page (https://www.embl.org/events/). Each event is a
<div data-event-item> with machine-readable attributes (date, type,
locations), so we read those instead of guessing from visible text.
Events whose registration is closed are skipped: you can't sign up anymore.
"""

from bs4 import BeautifulSoup

from helpers import clean, fetch, make_item, to_date, today

NAME = "embl"
URL = "https://www.embl.org/events/"

TYPE_MAP = {"course": "workshop", "conference": "conference", "webinar": "webinar"}
SITE_PLACES = {
    "heidelberg": "Heidelberg, Germany",
    "ebi": "Hinxton, UK",
    "barcelona": "Barcelona, Spain",
    "rome": "Rome, Italy",
    "hamburg": "Hamburg, Germany",
    "grenoble": "Grenoble, France",
}


def _mode_and_location(where):
    """'EMBL Heidelberg, Virtual' -> ('hybrid', 'Heidelberg, Germany')"""
    where = where.lower()
    places = list(dict.fromkeys(place for key, place in SITE_PLACES.items() if key in where))
    virtual = "virtual" in where or "online" in where
    if places and virtual:
        return "hybrid", "; ".join(places)
    if virtual:
        return "online", "Online"
    return "offline", "; ".join(places)


def _end_date(date_text, start):
    """'16 November - 20 November 2026' -> '2026-11-20'; a single date -> start."""
    if " - " not in date_text:
        return start
    return to_date(date_text.split(" - ")[-1].strip()) or start


def fetch_items():
    soup = BeautifulSoup(fetch(URL, kind="text"), "html.parser")
    items = []
    for div in soup.select("div[data-event-item]"):
        link = div.select_one("h3 a")
        start = div.get("data-event-date")
        if not link or not start:
            continue

        # Every "Registration: Closed" (and none open) means it's too late.
        statuses = div.select(".event-summary-card__status-value")
        if statuses and all("is-closed" in s.get("class", []) for s in statuses):
            continue

        badges = [clean(b.get_text()) for b in div.select(".vf-badge")]
        where = badges[0] if badges else div.get("data-event-locations", "")
        kind_badge = badges[1] if len(badges) > 1 else ""
        mode, location = _mode_and_location(where)
        if "EMBO" in kind_badge:
            organiser = "EMBO / EMBL"
        elif "EBI" in where or "EBI" in kind_badge:
            organiser = "EMBL-EBI"
        else:
            organiser = "EMBL"

        date_el = div.select_one(".vf-summary__date")
        end = _end_date(clean(date_el.get_text()) if date_el else "", start)
        speakers_el = div.select_one(".event-summary-card__speakers")
        speakers = clean(speakers_el.get_text()) if speakers_el else ""

        item = make_item(
            source=NAME,
            title=link.get_text(),
            organiser=organiser,
            type=TYPE_MAP.get(div.get("data-event-type"), "workshop"),
            mode=mode,
            location=location,
            start_date=start,
            end_date=end,
            # no published registration deadline: register before it starts
            deadline=start if start >= today().isoformat() else None,
            notes=f"Speakers: {speakers}" if speakers else "",
            url=link.get("href", ""),
            tag_text=f"{div.get('data-event-topics', '')} {kind_badge}",
            bio_source=True,
        )
        if item:
            items.append(item)
    return items
