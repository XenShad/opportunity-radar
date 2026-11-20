"""
TeSS - ELIXIR's Training eSupport System: a public registry of bioinformatics
courses, workshops, webinars and conferences across Europe and beyond.

How: TeSS's open JSON API (https://tess.elixir-europe.org/events.json).
By default it returns upcoming and ongoing events only.

Two passes:
  1. keyword searches (config.TESS_QUERIES), and
  2. TeSS's online events (online=true), which is where most webinars are.
     Online events are only kept if they match one of your field keywords,
     because this list also has general soft-skills sessions.

This file also provides event_to_item(), which embl_ebi.py reuses.
"""

import config
from helpers import fetch, guess_type, make_item, to_date, today

NAME = "tess"
API = "https://tess.elixir-europe.org/events.json"


def _type(ev):
    """TeSS event_types + title -> our type."""
    event_types = ev.get("event_types") or []
    title = ev.get("title") or ""
    online = bool(ev.get("online"))
    guessed = guess_type(title, default="", online=online)
    if guessed in ("summer-school", "hackathon", "webinar", "workshop", "competition"):
        return guessed
    if "meetings_and_conferences" in event_types or guessed == "conference":
        return "conference"
    # TeSS has no "webinar" category. An online session that starts and ends
    # on the same day, and isn't called a course or workshop, is a webinar
    # (e.g. EMBL-EBI's one-hour "Rebuilding microbial genomes with MGnify").
    start, end = to_date(ev.get("start")), to_date(ev.get("end"))
    if online and start and start == (end or start):
        return "webinar"
    return "workshop"


def _readable(values):
    """['first_come_first_served'] -> 'First come first served'"""
    return ", ".join(str(v).replace("_", " ").capitalize() for v in values or [] if v)


def event_to_item(ev, source, require_match=False):
    """
    One TeSS event -> our item.
    require_match=True keeps the event only if a field keyword matches
    (used for the broad online-events pass).
    """
    start, end = ev.get("start"), ev.get("end")
    starts_today_or_later = bool(start) and to_date(start) >= today().isoformat()
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
        # TeSS has no registration deadline. For upcoming events we use the
        # start date (registration closes by then at the latest). Ongoing
        # events get no deadline and disappear after their end date.
        deadline=start if starts_today_or_later else None,
        eligibility=_readable(ev.get("target_audience")) or _readable(ev.get("eligibility")),
        notes=f"Cost: {cost}" if cost else "",
        url=ev.get("url") or f"https://tess.elixir-europe.org/events/{ev.get('slug', '')}",
        tag_text=f"{keywords} {topics} {(ev.get('description') or '')[:1500]}",
        bio_source=not require_match,
        require_match=require_match,
    )


def fetch_items():
    items, seen = [], set()

    def add(events, require_match):
        for ev in events:
            if ev.get("id") in seen:
                continue
            seen.add(ev.get("id"))
            item = event_to_item(ev, NAME, require_match)
            if item:
                items.append(item)

    for query in config.TESS_QUERIES:
        add(fetch(API, params={"q": query, "per_page": config.TESS_PER_QUERY}), require_match=False)

    for page in range(1, config.TESS_ONLINE_PAGES + 1):
        events = fetch(API, params={"online": "true", "per_page": 100, "page": page})
        add(events, require_match=True)
        if len(events) < 100:                   # last page
            break
    return items
