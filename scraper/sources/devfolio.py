"""
Devfolio - Indian (and global) hackathons with open applications.

How: Devfolio's public JSON API (robots.txt allows everything).
Note: the API also returns participant profiles; we never store those.
"""

from helpers import fetch, make_item

NAME = "devfolio"
API = "https://api.devfolio.co/api/hackathons"
MAX_PAGES = 3


def fetch_items():
    items = []
    page, pages = 1, 1
    while page <= min(pages, MAX_PAGES):
        data = fetch(API, params={"filter": "application_open", "page": page})
        pages = data.get("pages") or 1
        for h in data.get("result") or []:
            setting = h.get("hackathon_setting") or {}
            if setting.get("is_hybrid"):
                mode = "hybrid"
            elif h.get("is_online"):
                mode = "online"
            else:
                mode = "offline"
            location = h.get("location") or ", ".join(
                p for p in (h.get("city"), h.get("state"), h.get("country")) if p
            )
            themes = ", ".join(t.get("name", "") for t in h.get("themes") or [])
            is_fellowship = h.get("fellowship") or h.get("type") == "FELLOWSHIP"

            item = make_item(
                source=NAME,
                title=h.get("name"),
                organiser=(h.get("hackathon_brand") or {}).get("name") or "",
                type="fellowship" if is_fellowship else "hackathon",
                mode=mode,
                location=location,
                start_date=h.get("starts_at"),
                end_date=h.get("ends_at"),
                deadline=setting.get("reg_ends_at") or h.get("starts_at"),
                eligibility=f"Teams of {h.get('team_min') or 1}–{h['team_size']}" if h.get("team_size") else "",
                url=f"https://{h['slug']}.devfolio.co/" if h.get("slug") else setting.get("site") or "",
                tag_text=f"{h.get('tagline') or ''} {themes} {(h.get('desc') or '')[:1500]}",
            )
            if item:
                items.append(item)
        page += 1
    return items
