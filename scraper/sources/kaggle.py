"""
Kaggle - data science and ML competitions (including CAFA-style bio rounds).

How: Kaggle's official REST API. It needs your API credentials, which are read
from environment variables (set as GitHub Secrets, see README):

    KAGGLE_USERNAME + KAGGLE_KEY   (from the kaggle.json file Kaggle gives you)
or  KAGGLE_API_TOKEN               (newer single-token style)

For local runs it also reads ~/.kaggle/kaggle.json if present.
With no credentials the source is skipped with a warning (no crash).
"""

import json
import os
from pathlib import Path

import config
from helpers import SourceSkipped, fetch, make_item

NAME = "kaggle"
API = "https://www.kaggle.com/api/v1/competitions/list"


def _credentials():
    """Return keyword arguments for fetch(): either auth=(user, key) or headers."""
    user, key = os.environ.get("KAGGLE_USERNAME"), os.environ.get("KAGGLE_KEY")
    if user and key:
        return {"auth": (user, key)}
    token = os.environ.get("KAGGLE_API_TOKEN")
    if token:
        return {"headers": {"Authorization": f"Bearer {token}"}}
    local = Path.home() / ".kaggle" / "kaggle.json"
    if local.exists():
        saved = json.loads(local.read_text())
        return {"auth": (saved["username"], saved["key"])}
    raise SourceSkipped("no Kaggle credentials; add KAGGLE_USERNAME and KAGGLE_KEY secrets")


def _get(record, *names):
    """Kaggle has used both camelCase and snake_case keys over the years."""
    for name in names:
        if record.get(name) not in (None, ""):
            return record[name]
    return None


def fetch_items():
    creds = _credentials()
    items = []
    for page in range(1, config.KAGGLE_PAGES + 1):
        batch = fetch(API, params={"page": page, "category": "all"}, **creds)
        if not batch:
            break
        for c in batch:
            ref = str(_get(c, "ref") or "")
            url = _get(c, "url") or (ref if ref.startswith("http")
                                     else f"https://www.kaggle.com/competitions/{ref}")
            tags = " ".join(t.get("name", "") for t in (c.get("tags") or []) if isinstance(t, dict))
            reward = _get(c, "reward") or ""
            category = _get(c, "category") or ""

            item = make_item(
                source=NAME,
                title=_get(c, "title"),
                organiser=_get(c, "organizationName", "organization_name") or "Kaggle",
                type="competition",
                mode="online",
                start_date=_get(c, "enabledDate", "enabled_date"),
                end_date=_get(c, "deadline"),
                # the last day new people can join, if Kaggle provides it
                deadline=_get(c, "newEntrantDeadline", "new_entrant_deadline", "deadline"),
                stipend_or_prize=reward,
                eligibility=f"Kaggle {category} competition" if category else "",
                url=url,
                tag_text=f"{_get(c, 'description') or ''} {tags}",
            )
            if item:
                items.append(item)
    return items
