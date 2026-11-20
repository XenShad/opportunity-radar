"""
Zindi - data science and ML competitions with cash prizes (often health,
agriculture and climate data; open to participants worldwide).

How: Zindi's public JSON API (https://api.zindi.africa/v1/competitions).
Only competitions that are open, public and need no secret code are kept.
"""

from helpers import fetch, make_item

NAME = "zindi"
API = "https://api.zindi.africa/v1/competitions"


def fetch_items():
    data = fetch(API, params={"per_page": 50}).get("data", [])
    items = []
    for c in data:
        if not c.get("open") or c.get("is_access_restricted") or c.get("secret_code_required"):
            continue
        org = c.get("organization")
        if isinstance(org, dict):               # in case the API ever returns an object
            org = org.get("name")
        item = make_item(
            source=NAME,
            title=c.get("title"),
            organiser=org or "Zindi",
            type="hackathon" if c.get("kind") == "hackathon" else "competition",
            mode="online",
            start_date=c.get("start_time"),
            end_date=c.get("end_time"),
            deadline=c.get("entries_close_at") or c.get("end_time"),
            stipend_or_prize=(c.get("reward") or "").replace(" ", " "),
            eligibility="Beginner friendly" if c.get("is_beginner_friendly") else "",
            url=f"https://zindi.africa/competitions/{c.get('id')}",
            tag_text="machine learning data science",
        )
        if item:
            items.append(item)
    return items
