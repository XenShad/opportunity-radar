"""
helpers.py - small building blocks shared by every source.

Sections:
  1. Errors           - special exceptions update.py knows how to handle
  2. Logging          - warn() collects warnings for the end-of-run summary
  3. robots.txt       - checks we are allowed to fetch a URL before fetching it
  4. HTTP             - fetch() with timeouts, retries and polite delays
  5. Dates            - turn messy date strings into "YYYY-MM-DD"
  6. Text             - HTML -> plain text, keyword tagging, type guessing
  7. make_item()      - builds one opportunity in the shared schema
"""

import hashlib
import html
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

import config

# All dates are shown in Indian Standard Time (UTC+5:30, no daylight saving).
IST = timezone(timedelta(hours=5, minutes=30))

# The allowed values for the "type" and "mode" fields.
TYPES = [
    "hackathon", "internship", "fellowship", "competition",
    "conference", "workshop", "webinar", "summer-school",
]
MODES = ["online", "offline", "hybrid"]


def today():
    """Today's date in India (GitHub's servers run on UTC)."""
    return datetime.now(IST).date()


# ---------------------------------------------------------------------------
# 1. Errors
# ---------------------------------------------------------------------------
class SourceBlocked(Exception):
    """The site said no (robots.txt, HTTP 401/403/429). Skip it, don't crash."""


class SourceSkipped(Exception):
    """We chose not to run this source (for example, no API key configured)."""


# ---------------------------------------------------------------------------
# 2. Logging
# ---------------------------------------------------------------------------
# update.py sets CURRENT_SOURCE before calling each source, so warnings can
# be grouped by source in the summary.
CURRENT_SOURCE = "-"
WARNINGS = []   # list of (source_name, message)


def warn(message):
    """Print a warning now and remember it for the summary."""
    print(f"  ! [{CURRENT_SOURCE}] {message}")
    WARNINGS.append((CURRENT_SOURCE, message))


# ---------------------------------------------------------------------------
# 3. robots.txt
# ---------------------------------------------------------------------------
# Python has urllib.robotparser, but it ignores "*" and "$" wildcards, which
# many sites use (e.g. "Allow: /api/public/*"). This small parser follows
# Google's rules: the longest matching rule wins, and Allow wins a tie.

_ROBOTS_CACHE = {}          # "https://host" -> list of (allow, regex, length)
_BOT_TOKEN = "opportunityradarbot"


def _robots_rule_to_regex(path_pattern):
    """'/api/*/x$' -> regex that matches the start of a URL path."""
    ends_with_dollar = path_pattern.endswith("$")
    if ends_with_dollar:
        path_pattern = path_pattern[:-1]
    regex = re.escape(path_pattern).replace(r"\*", ".*")
    return re.compile(regex + ("$" if ends_with_dollar else ""))


def _parse_robots(text):
    """Return the rules that apply to us: our own group if present, else '*'."""
    groups = []                 # list of (set_of_agents, list_of_rules)
    agents, rules = set(), []
    last_was_agent = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if not last_was_agent and (agents or rules):
                groups.append((agents, rules))      # previous group finished
                agents, rules = set(), []
            agents.add(value.lower())
            last_was_agent = True
        elif key in ("allow", "disallow"):
            last_was_agent = False
            if value:                               # "Disallow:" (empty) = allow all
                rules.append((key == "allow", _robots_rule_to_regex(value), len(value)))
    if agents or rules:
        groups.append((agents, rules))

    ours = [r for a, r in groups if any(_BOT_TOKEN in agent for agent in a)]
    star = [r for a, r in groups if "*" in a]
    chosen = ours or star
    return [rule for group in chosen for rule in group]   # flatten


def robots_allows(url):
    """True if robots.txt lets us fetch this URL."""
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in _ROBOTS_CACHE:
        try:
            r = requests.get(origin + "/robots.txt", timeout=config.REQUEST_TIMEOUT,
                             headers={"User-Agent": config.USER_AGENT})
        except requests.RequestException as e:
            raise SourceBlocked(f"could not read {origin}/robots.txt ({e})")
        if r.status_code == 200:
            _ROBOTS_CACHE[origin] = _parse_robots(r.text)
        elif 400 <= r.status_code < 500:
            _ROBOTS_CACHE[origin] = []              # no robots.txt = no rules
        else:
            raise SourceBlocked(f"{origin}/robots.txt returned HTTP {r.status_code}")

    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    best = None                                     # (allow, length)
    for allow, regex, length in _ROBOTS_CACHE[origin]:
        if regex.match(path):
            if best is None or length > best[1] or (length == best[1] and allow):
                best = (allow, length)
    return True if best is None else best[0]


# ---------------------------------------------------------------------------
# 4. HTTP
# ---------------------------------------------------------------------------
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": config.USER_AGENT})
_LAST_REQUEST_AT = {}       # host -> time.monotonic() of the last request


def fetch(url, params=None, headers=None, auth=None, kind="json", retries=2):
    """
    Download a URL politely and return its content.

    kind = "json"  -> parsed JSON (dict/list)
           "text"  -> str (for HTML pages)
           "bytes" -> raw bytes (best for RSS: feedparser detects the encoding)

    Raises SourceBlocked if robots.txt forbids it or the site refuses us.
    """
    if params:
        url = url + ("&" if "?" in url else "?") + urlencode(params, doseq=True)

    if not robots_allows(url):
        raise SourceBlocked(f"robots.txt disallows {url}")

    host = urlsplit(url).netloc
    wait = config.DELAY_BETWEEN_REQUESTS - (time.monotonic() - _LAST_REQUEST_AT.get(host, 0))
    if wait > 0:
        time.sleep(wait)

    for attempt in range(retries + 1):
        _LAST_REQUEST_AT[host] = time.monotonic()
        try:
            r = _SESSION.get(url, headers=headers, auth=auth, timeout=config.REQUEST_TIMEOUT)
        except requests.RequestException as e:
            if attempt == retries:
                raise
            time.sleep(2 * (attempt + 1))           # wait 2s, then 4s, then give up
            continue

        if r.status_code in (401, 403, 429):
            raise SourceBlocked(f"HTTP {r.status_code} from {host}")
        if r.status_code >= 500 and attempt < retries:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()

        if kind == "json":
            return r.json()
        if kind == "bytes":
            return r.content
        # No charset in the header? requests then assumes Latin-1, which turns
        # "Who’s" into "Whoâs". Modern pages are almost always UTF-8.
        if "charset" not in r.headers.get("content-type", "").lower():
            r.encoding = "utf-8"
        return r.text


# ---------------------------------------------------------------------------
# 5. Dates
# ---------------------------------------------------------------------------
_DATE_FORMATS = [
    "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d %m %Y",
]


def to_date(value):
    """
    Turn almost anything date-like into "YYYY-MM-DD" (or None).

    Handles: datetime/date objects, feedparser time tuples, ISO strings like
    "2026-11-28T17:30:00+05:30" or "...Z", and human strings like
    "Dec 04, 2026", "30th November 2026", "30/11/2026".
    Times with a timezone are converted to India time first, so a deadline of
    "2026-11-21T18:30:00Z" correctly becomes 22 Nov in India.
    """
    if not value:
        return None
    if isinstance(value, time.struct_time):         # from feedparser
        value = datetime(*value[:6], tzinfo=timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo:
            value = value.astimezone(IST)
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    try:
        return to_date(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass

    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", text, flags=re.I)  # 30th -> 30
    text = re.sub(r"\bSept\b", "Sep", text, flags=re.I)
    if re.search(r"[A-Za-z]", text):                # "30-Nov-2026" -> "30 Nov 2026"
        text = re.sub(r"[-/.,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


_DATE_IN_TEXT = (
    r"(\d{1,2}(?:st|nd|rd|th)?[\s\-/.]+(?:[A-Za-z]{3,9}|\d{1,2})[\s\-/.,]+\d{4}"
    r"|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
)
_DEADLINE_RX = re.compile(
    r"(?:last\s+date|deadline|apply\s+(?:by|before)|closing\s+date|last\s+day"
    r"|applications?\s+close[sd]?|due\s+date|register\s+(?:by|before))"
    r"[^0-9A-Za-z]{0,15}(?:(?:to|for|of)\s+\w+\s*)?(?:is|on|:|-)?\s*" + _DATE_IN_TEXT,
    re.I,
)


def find_deadline_in_text(text):
    """
    Look for phrases like "Last date: 30 November 2026" in free text.
    Returns "YYYY-MM-DD" or None. Only accepts dates within a sensible window,
    so a random year in the text doesn't become a deadline.
    """
    if not text:
        return None
    lo, hi = today() - timedelta(days=60), today() + timedelta(days=500)
    for match in _DEADLINE_RX.finditer(text):
        found = to_date(match.group(1))
        if found and lo <= date.fromisoformat(found) <= hi:
            return found
    return None


# ---------------------------------------------------------------------------
# 6. Text
# ---------------------------------------------------------------------------
def html_to_text(raw_html):
    """'<p>Hello <b>world</b></p>' -> 'Hello world'"""
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(" ")
    return clean(text)


def clean(text):
    """Unescape HTML entities and squash whitespace."""
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip()


def shorten(text, limit=160):
    text = clean(text)
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _keyword_regex(keyword):
    r"""
    'genom*' -> \bgenom\w*   'ml' -> \bml\b   (\b = word boundary)
    A space in a keyword also matches a hyphen, so "life science*" finds
    "life sciences" and "life-sciences".
    """
    keyword = keyword.lower().strip()
    prefix = keyword.endswith("*")
    body = re.escape(keyword.rstrip("*")).replace(r"\ ", " ").replace(" ", r"[\s-]+")
    return r"\b" + body + (r"\w*" if prefix else r"\b")


# Compile one regex per field once, at import time (fast to reuse).
_FIELD_REGEXES = {
    field: re.compile("|".join(_keyword_regex(k) for k in keywords), re.I)
    for field, keywords in config.FIELD_KEYWORDS.items()
}


def match_fields(text):
    """Return the list of field tags whose keywords appear in the text."""
    return [field for field, regex in _FIELD_REGEXES.items() if regex.search(text or "")]


_INDIA_RX = re.compile("|".join(_keyword_regex(p) for p in config.INDIA_PLACES), re.I)


def find_india_place(text):
    """'ICAR-NBAIR Bengaluru SRF Walk-In' -> 'Bengaluru' (or None)."""
    match = _INDIA_RX.search(text or "")
    if not match:
        return None
    place = match.group(0)
    return place.upper() if len(place) <= 5 else place.title()   # IIT, AIIMS stay upper-case


def guess_region(location, mode):
    """India | Online | International"""
    if _INDIA_RX.search(location or ""):
        return "India"
    if mode == "online":
        return "Online"
    return "International"


# Order matters: the first rule that matches wins.
_TYPE_RULES = [
    ("summer-school", r"\b(summer|winter|spring|autumn) school\b"),
    ("hackathon",     r"\bhackathon|\bhack\b|\bdatathon|\bbuildathon|\bcodeathon|\bcode-a-thon|\bsprint\b"),
    ("webinar",       r"\bwebinar|\bweb seminar|\bonline talk|\bseminar series|\bbytesize\b"
                      r"|\blive session|\binfo(rmation)? session"),
    ("conference",    r"\bconference|\bsymposium|\bcongress\b|\bsummit\b|\bmeeting\b"),
    ("internship",    r"\bintern(ship)?s?\b|\bsummer (training|research|program)|\btrainee"),
    ("fellowship",    r"\bfellowship|\bscholarship|\bjrf\b|\bsrf\b"),
    ("competition",   r"\bcompetition|\bchallenge\b|\bcontest|\bquiz|\bolympiad"),
    ("workshop",      r"\bworkshop|\btraining|\bcourse\b|\bbootcamp|\bhands-on|\btutorial"),
]

# Words that mean "a talk" - a webinar only when it happens online
# (an in-person "seminar" or "lecture" is not a webinar).
_ONLINE_TALK_RX = re.compile(
    r"\bseminar|\btalks?\b|\blecture|\bkeynote|\bmasterclass|\boffice hours|\bjournal club|\bq\s?&\s?a\b",
    re.I,
)


def guess_type(text, default, online=False):
    """
    Guess the opportunity type from a title. Falls back to `default`.
    Pass online=True for online events, so talks/seminars count as webinars.
    """
    for kind, pattern in _TYPE_RULES:
        if re.search(pattern, text or "", re.I):
            return kind
    if online and _ONLINE_TALK_RX.search(text or ""):
        return "webinar"
    return default


def find_event_date_in_text(text):
    """
    First date in the text that is today or later, e.g. the date in
    "Join our webinar on Wednesday, December 10, 2026 at 12 PM ET".
    Returns "YYYY-MM-DD" or None.
    """
    lo, hi = today(), today() + timedelta(days=500)
    for match in re.finditer(_DATE_IN_TEXT, text or ""):
        found = to_date(match.group(1))
        if found and lo <= date.fromisoformat(found) <= hi:
            return found
    return None


# ---------------------------------------------------------------------------
# 7. make_item()
# ---------------------------------------------------------------------------
def normalise_url(url):
    """Lower-case the host, drop tracking params (utm_*), #fragments and trailing '/'."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, query, ""))


def make_id(*parts):
    """A short, stable ID: the same inputs always give the same ID."""
    joined = "|".join(str(p or "").strip().lower() for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]


def make_item(*, source, title, url, type, organiser="", mode="online",
              location="", start_date=None, end_date=None, deadline=None,
              stipend_or_prize="", eligibility="", notes="", tag_text="",
              bio_source=False, require_match=False, fields=None):
    """
    Build one opportunity dict in the shared schema.

    tag_text      : extra text (description, themes...) used ONLY for keyword tagging.
    bio_source    : True for biology-specific sources. Unmatched items get the
                    BIO_FALLBACK_FIELD tag instead of being treated as general.
    require_match : True to drop the item if no field keyword matches
                    (used for fuzzy searches that return off-topic results).

    fields        : tags the source already worked out; skips keyword matching.

    Returns None when the item should be skipped.
    """
    title = clean(title)
    if not title or not url:
        return None
    if type not in TYPES:
        raise ValueError(f"unknown type {type!r} for {title!r}; must be one of {TYPES}")
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r} for {title!r}; must be one of {MODES}")

    fields = fields or match_fields(f"{title} {clean(tag_text)[:config.TAG_TEXT_MAX_CHARS]}")
    if not fields:
        if bio_source:
            fields = [config.BIO_FALLBACK_FIELD]
        elif require_match or not config.KEEP_GENERAL_ITEMS:
            return None
        else:
            fields = [config.GENERAL_FIELD]

    location = clean(location) or ("Online" if mode == "online" else "")
    start, end = to_date(start_date), to_date(end_date)
    # "ABiMS (https://abims.fr/), BiGEst (https://...)" -> "ABiMS, BiGEst"
    organiser = shorten(re.sub(r"\s*\(\s*https?://[^)]*\)", "", clean(organiser)), 90)
    return {
        "id": make_id(source, normalise_url(url), title, start),
        "title": title,
        "organiser": organiser,
        "type": type,
        "fields": fields,
        "mode": mode,
        "location": location,
        # no location given? the title often names the city ("Hack Pune 2026")
        "region": guess_region(location if location else title, mode),
        "start_date": start,
        "end_date": end,
        "deadline": to_date(deadline),
        "stipend_or_prize": clean(stipend_or_prize),
        "eligibility": shorten(eligibility, 200),
        "url": url.strip(),
        "source": source,
        "date_added": None,                 # filled in by update.py
        "verified": source in config.VERIFIED_SOURCES,
        "notes": shorten(notes, 200),
    }
