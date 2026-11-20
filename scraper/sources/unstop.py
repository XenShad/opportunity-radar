"""
Unstop - Indian hackathons, competitions, internships and workshops.

How: Unstop's public JSON API. Their robots.txt explicitly allows
/api/public/* while blocking the rest of /api/.

We fetch:
  - the first few pages of open hackathons (general list), and
  - a keyword search for each type in config.UNSTOP_SEARCH_TYPES.
Unstop's search is fuzzy (a "biotech" search can return a design internship),
so search results are only kept if they match one of our field keywords.
"""

import config
from helpers import fetch, html_to_text, make_item, guess_type

NAME = "unstop"
API = "https://unstop.com/api/public/opportunity/search-result"


def _search(opportunity, page=1, per_page=30, term=None):
    """One page of results from the Unstop API."""
    params = {"opportunity": opportunity, "page": page, "per_page": per_page, "oppstatus": "open"}
    if term:
        params["searchTerm"] = term
    data = fetch(API, params=params)
    return (data.get("data") or {}).get("data") or []


def _rupees(amount):
    return f"₹{int(amount):,}"


def _prize_text(rec):
    """Stipend for internships, total cash prize for competitions."""
    job = rec.get("jobDetail") or {}
    if job.get("max_salary"):
        low, high = job.get("min_salary") or job["max_salary"], job["max_salary"]
        span = _rupees(high) if low == high else f"{_rupees(low)}–{_rupees(high)}"
        return f"{span}/month stipend"
    prizes = rec.get("prizes") or []
    cash = sum(p.get("cash") or 0 for p in prizes if p.get("currency") in (None, "fa-rupee"))
    if cash:
        return f"{_rupees(cash)} in prizes"
    if any(p.get("certificate") for p in prizes):
        return "Certificates"
    return ""


def _location(rec):
    cities = [loc.get("city") for loc in rec.get("locations") or [] if loc.get("city")]
    if cities:
        return ", ".join(dict.fromkeys(cities)) + ", India"     # dict.fromkeys = de-duplicate
    addr = rec.get("address_with_country_logo") or {}
    country = addr.get("country")
    if isinstance(country, dict):                               # sometimes {"name": "India", ...}
        country = country.get("name")
    return ", ".join(p for p in (addr.get("city"), addr.get("state"), country) if p)


def _mode(rec):
    job_type = (rec.get("jobDetail") or {}).get("type")         # internships: in_office / wfh / hybrid
    if job_type == "hybrid":
        return "hybrid"
    if job_type in ("wfh", "remote"):
        return "online"
    if job_type:
        return "offline"
    return "online" if rec.get("region") == "online" else "offline"


def _type(rec):
    kind, sub = rec.get("type"), rec.get("subtype") or ""
    if kind == "hackathons":
        return "hackathon"
    if sub == "internships" or kind == "internships":
        return "internship"
    if kind == "scholarships":
        return "fellowship"
    if kind == "workshops":
        return guess_type(rec.get("title"), "workshop", online=_mode(rec) == "online")
    return "competition"


def _to_item(rec, require_match):
    organisation = rec.get("organisation") or {}
    regn = rec.get("regnRequirements") or {}
    eligible = [f.get("name") for f in rec.get("filters") or [] if f.get("type") == "eligible"]
    skills = [s.get("skill_name") or s.get("skill") or "" for s in rec.get("required_skills") or []]
    functions = [w.get("name") or "" for w in rec.get("workfunction") or []]
    details = html_to_text(rec.get("details") or "")[:1500]

    mode = _mode(rec)
    return make_item(
        source=NAME,
        title=rec.get("title"),
        organiser=organisation.get("name"),
        type=_type(rec),
        mode=mode,
        location=_location(rec) or ("Online" if mode == "online" else "India"),
        end_date=rec.get("end_date"),
        deadline=regn.get("end_regn_dt") or rec.get("end_date"),
        stipend_or_prize=_prize_text(rec),
        eligibility=", ".join(eligible),
        url=rec.get("seo_url") or f"https://unstop.com/{rec.get('public_url', '')}",
        tag_text=" ".join(functions + skills) + " " + details,
        require_match=require_match,
    )


def fetch_items():
    records = []                                # (record, require_match)
    for page in range(1, config.UNSTOP_HACKATHON_PAGES + 1):
        records += [(r, False) for r in _search("hackathons", page)]
    for kind in config.UNSTOP_SEARCH_TYPES:
        for term in config.UNSTOP_SEARCH_TERMS:
            records += [(r, True) for r in _search(kind, 1, 20, term)]

    items, seen = [], set()
    for rec, require_match in records:
        if rec.get("id") in seen:               # the same listing can match several searches
            continue
        seen.add(rec.get("id"))
        item = _to_item(rec, require_match)
        if item:
            items.append(item)
    return items
