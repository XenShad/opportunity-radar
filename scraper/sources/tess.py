"""
TeSS - ELIXIR's Training eSupport System: a public registry of bioinformatics
courses, workshops, webinars and conferences across Europe and beyond.

How: TeSS's open JSON API (https://tess.elixir-europe.org/events.json).
By default it returns upcoming and ongoing events only.

This file also provides event_to_item(), which embl_ebi.py reuses.
"""

import config
from helpers import fetch, make_item, guess_type, today

NAME = "tess"
API = "https://tess.elixir-europe.org/events.json"


def _type(ev):
    """TeSS event_types + title -> our type."""
    event_types = ev.get("event_types") or []
    title = ev.get("title") or ""
    guessed = guess_type(title, default="")
    if guessed in ("summer-school", "hackathon", "webinar"):
        return guessed
    if "meetings_and_conferences" in event_types:
        return "conference"
    return guessed if guessed in ("conference", "competition") else "workshop"


def _readable(values):
    """['first_come_first_served'] -> 'First come first served'"""
    return ", ".join(str(v).replace("_", " ").capitalize() for v in values or [] if v)


def event_to_item(ev, source):
    start, end = ev.get("start"), ev.get("end")
    starts_in_future = bool(start) and start[:10] > today().isoformat()
    online = bool(ev.get("online"))
    location = ", ".join(p for p in (ev.get("city"), ev.get("country")) if p)
    topics = " ".join(t.get("preferred_label", "") for t in ev.get("scientific_topics") or [])
    keywords = " ".join(ev.get("keywords") or [])
    cost = _readable([ev.get("cost_basis")]) if ev.get("cost_basis") else ""

    return make_item(
        source=source,
        title=ev.get("title"),
        organiser=ev.get("organizer") or "",
        type=_type(ev),
        mode="online" if online else "offline",
        location=location or ("Online" if online else ""),
        start_date=start,
        end_date=end,
        # TeSS has no registration deadline. For future events we use the
        # start date (registration closes by then at the latest). Ongoing
        # events get no deadline and disappear after their end date.
        deadline=start if starts_in_future else None,
        eligibility=_readable(ev.get("target_audience")) or _readable(ev.get("eligibility")),
        notes=f"Cost: {cost}" if cost else "",
        url=ev.get("url") or f"https://tess.elixir-europe.org/events/{ev.get('slug', '')}",
        tag_text=f"{keywords} {topics} {(ev.get('description') or '')[:1500]}",
        bio_source=True,
    )


def fetch_items():
    items, seen = [], set()
    for query in config.TESS_QUERIES:
        events = fetch(API, params={"q": query, "per_page": config.TESS_PER_QUERY})
        for ev in events:
            if ev.get("id") in seen:
                continue
            seen.add(ev.get("id"))
            item = event_to_item(ev, NAME)
            if item:
                items.append(item)
    return items
