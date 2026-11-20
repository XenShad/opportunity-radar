"""
update.py - rebuilds data/opportunities.json.

Run it from the project folder:
    python scraper/update.py                 # fetch every enabled source
    python scraper/update.py --only tess     # fetch just one source (others keep old data)
    python scraper/update.py --custom-only   # no internet: just re-merge custom.json

Steps:
  1. Load the previous opportunities.json (to remember date_added and to keep
     a source's old items if that source fails this time).
  2. Run each enabled source. A failing source logs a warning; it never
     crashes the whole run.
  3. Load data/custom.json (your own entries).
  4. Remove duplicates, drop expired items, sort by deadline.
  5. Write data/opportunities.json and print a summary.
"""

import argparse
import json
import re
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
import helpers
from helpers import SourceBlocked, SourceSkipped, normalise_url, today
from sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
OPPORTUNITIES_PATH = ROOT / "data" / "opportunities.json"
CUSTOM_PATH = ROOT / "data" / "custom.json"

SCHEMA_KEYS = [
    "id", "title", "organiser", "type", "fields", "mode", "location", "region",
    "start_date", "end_date", "deadline", "stipend_or_prize", "eligibility",
    "url", "source", "date_added", "verified",
]
OPTIONAL_KEYS = ["notes", "expected"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: {path.name} is not valid JSON (line {e.lineno}: {e.msg}). Fix it and re-run.")


def load_custom():
    """Read custom.json and fill in anything you left out."""
    raw = load_json(CUSTOM_PATH, {"items": []})
    entries = raw.get("items", raw) if isinstance(raw, dict) else raw
    items = []
    for n, entry in enumerate(entries, start=1):
        title, url, kind = entry.get("title"), entry.get("url"), entry.get("type")
        if not (title and url and kind in helpers.TYPES):
            print(f"  ! custom.json item #{n} skipped: needs title, url and a valid type {helpers.TYPES}")
            continue
        mode = entry.get("mode") if entry.get("mode") in helpers.MODES else "offline"
        location = entry.get("location") or ("Online" if mode == "online" else "")
        item = {
            # same rule as slugify() in assets/js/utils.js, so the site and
            # this script agree on the id of an entry that has none
            "id": entry.get("id") or "custom-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
            "title": helpers.clean(title),
            "organiser": entry.get("organiser", ""),
            "type": kind,
            "fields": entry.get("fields") or helpers.match_fields(f"{title} {entry.get('eligibility', '')}")
                      or [config.BIO_FALLBACK_FIELD],
            "mode": mode,
            "location": location,
            "region": entry.get("region") or helpers.guess_region(location, mode),
            "start_date": helpers.to_date(entry.get("start_date")),
            "end_date": helpers.to_date(entry.get("end_date")),
            "deadline": helpers.to_date(entry.get("deadline")),
            "stipend_or_prize": entry.get("stipend_or_prize", ""),
            "eligibility": entry.get("eligibility", ""),
            "url": url,
            "source": "custom",
            "date_added": entry.get("date_added"),
            "verified": True,
            "notes": entry.get("notes", ""),
        }
        if entry.get("expected"):
            item["expected"] = True
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
def title_key(item):
    """Same title + same start date = same opportunity, even from two sites."""
    words = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
    return f"{words}|{item.get('start_date') or ''}"


def completeness(item):
    return sum(1 for k in SCHEMA_KEYS if item.get(k))


def dedupe(items):
    """
    Keep one copy of each opportunity. Preference: your custom entries first,
    then verified sources, then whichever copy has more fields filled in.
    Field tags from all copies are combined.
    """
    ranked = sorted(items, key=lambda i: (i["source"] != "custom", not i["verified"],
                                          -completeness(i), sort_key(i)))
    kept, by_key = [], {}
    for item in ranked:
        keys = ["url:" + normalise_url(item["url"]), "title:" + title_key(item), "id:" + item["id"]]
        existing = next((by_key[k] for k in keys if k in by_key), None)
        if existing:
            existing["fields"] = list(dict.fromkeys(existing["fields"] + item["fields"]))
            continue
        kept.append(item)
        for k in keys:
            by_key[k] = item
    return kept


def is_expired(item, day):
    """
    Expired if the deadline has passed. With no deadline, expired if the end
    date has passed. Scraped items with no dates at all expire
    UNDATED_ITEM_MAX_DAYS after we first saw them.
    """
    iso = day.isoformat()
    if item.get("deadline"):
        return item["deadline"] < iso
    if item.get("end_date"):
        return item["end_date"] < iso
    if item.get("start_date") or item["source"] == "custom":
        return False
    first_seen = item.get("date_added") or iso
    return date.fromisoformat(first_seen) < day - timedelta(days=config.UNDATED_ITEM_MAX_DAYS)


def sort_key(item):
    """Soonest deadline first, then future start dates, then ongoing items by end date, undated last."""
    if item.get("deadline"):
        key = item["deadline"]
    elif item.get("start_date") and item["start_date"] >= today().isoformat():
        key = item["start_date"]
    else:
        key = item.get("end_date") or "9999-12-31"
    return (key, item["title"].lower())


def tidy(item):
    """Fixed key order, optional keys only when used. Makes diffs easy to read."""
    out = {k: item.get(k) for k in SCHEMA_KEYS}
    for k in OPTIONAL_KEYS:
        if item.get(k):
            out[k] = item[k]
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_sources(only, previous_by_source):
    """Run each source. Returns (items, stats)."""
    items, stats = [], {}
    for name, fetch_items in SOURCES.items():
        if only and name != only:
            items += previous_by_source.get(name, [])
            continue
        if not config.ENABLED_SOURCES.get(name, False):
            stats[name] = {"status": "disabled", "count": 0}
            continue

        helpers.CURRENT_SOURCE = name
        started = time.monotonic()
        print(f"- {name} ...", flush=True)
        try:
            found = fetch_items()
            items += found
            stats[name] = {"status": "ok", "count": len(found)}
            print(f"  {len(found)} items in {time.monotonic() - started:.1f}s")
        except Exception as e:  # any error in one source must not stop the others
            kept = previous_by_source.get(name, [])
            items += kept               # keep last run's items so they don't vanish
            if isinstance(e, SourceSkipped):
                status = "skipped"
            elif isinstance(e, SourceBlocked):
                status = "blocked"
            else:
                status = "failed"
                traceback.print_exc(limit=2)
            stats[name] = {"status": status, "count": 0, "kept_from_last_run": len(kept), "message": str(e)[:200]}
            helpers.warn(f"{status}: {e} (kept {len(kept)} items from last run)")
    helpers.CURRENT_SOURCE = "-"
    return items, stats


def main():
    # Windows terminals sometimes can't print characters like ₹; never crash on that.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Update data/opportunities.json")
    parser.add_argument("--only", choices=sorted(SOURCES), help="run just this source")
    parser.add_argument("--custom-only", action="store_true", help="don't fetch anything, just re-merge custom.json")
    args = parser.parse_args()

    day = today()
    previous = load_json(OPPORTUNITIES_PATH, {"meta": {}, "items": []})
    previous_items = {i["id"]: i for i in previous.get("items", [])}
    previous_by_source = {}
    for item in previous.get("items", []):
        if item["source"] != "custom":
            previous_by_source.setdefault(item["source"], []).append(item)

    print(f"Opportunity Radar update - {day.isoformat()} (India time)\n")
    if args.custom_only:
        scraped = [i for items in previous_by_source.values() for i in items]
        stats = previous.get("meta", {}).get("sources", {})
        print("--custom-only: reusing scraped items from the last run")
    else:
        scraped, stats = run_sources(args.only, previous_by_source)
        if args.only:   # keep the other sources' stats from last time
            stats = {**previous.get("meta", {}).get("sources", {}), **stats}

    custom = load_custom()
    everything = custom + scraped

    # date_added: keep the date we first saw an item; new items get today.
    for item in everything:
        old = previous_items.get(item["id"])
        item["date_added"] = (old or {}).get("date_added") or item.get("date_added") or day.isoformat()

    # Drop expired items BEFORE removing duplicates, so that if a course runs
    # several times under one URL, the next open session survives.
    expired = [i for i in everything if is_expired(i, day)]
    current = dedupe([i for i in everything if not is_expired(i, day)])
    current = [tidy(i) for i in sorted(current, key=sort_key)]

    current_ids = {i["id"] for i in current}
    expired_ids = {i["id"] for i in expired}
    expired_count = len({title_key(i) for i in expired})
    new_items = [i for i in current if i["id"] not in previous_items]
    gone = [i for i_id, i in previous_items.items() if i_id not in current_ids and i_id not in expired_ids]

    all_fields = sorted({f for i in current for f in i["fields"]} | set(config.FIELD_KEYWORDS))
    output = {
        "meta": {
            "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": len(current),
            "sources": stats,
            "fields": all_fields,
            "types": helpers.TYPES,
            "manual_sources": config.MANUAL_SOURCES,
        },
        "items": current,
    }
    OPPORTUNITIES_PATH.parent.mkdir(exist_ok=True)
    OPPORTUNITIES_PATH.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- summary ----------------------------------------------------------
    print("\n================ SUMMARY ================")
    print(f"{'source':<14}{'status':<10}{'items':>6}")
    for name, s in stats.items():
        extra = f"  (kept {s['kept_from_last_run']} old)" if s.get("kept_from_last_run") else ""
        print(f"{name:<14}{s['status']:<10}{s.get('count', 0):>6}{extra}")
    print(f"{'custom':<14}{'ok':<10}{len(custom):>6}")
    print("-----------------------------------------")
    print(f"open opportunities written : {len(current)}")
    print(f"new since last run         : {len(new_items)}")
    print(f"removed (deadline passed)  : {expired_count}")
    print(f"removed (no longer listed) : {len(gone)}")
    failed = [n for n, s in stats.items() if s["status"] in ("failed", "blocked")]
    skipped = [n for n, s in stats.items() if s["status"] == "skipped"]
    print(f"failed / blocked sources   : {', '.join(failed) or 'none'}")
    if skipped:
        print(f"skipped sources            : {', '.join(skipped)}")
    expired_custom = [i["title"] for i in expired if i["source"] == "custom"]
    for title in expired_custom:
        print(f"  note: custom entry has expired, you can delete it from custom.json: {title}")
    if helpers.WARNINGS:
        print(f"warnings                   : {len(helpers.WARNINGS)} (see '!' lines above)")
    print(f"\nWrote {OPPORTUNITIES_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
