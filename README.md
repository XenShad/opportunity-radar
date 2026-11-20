# Opportunity Radar

A personal dashboard of **hackathons, internships, fellowships, competitions, conferences, workshops and summer schools**, focused on computational biology but easy to point at other fields.

- **Free to host:** a static site on GitHub Pages.
- **Updates itself:** a GitHub Actions job runs a Python scraper every 6 hours and commits fresh data.
- **Private:** no login, no tracking, no external fonts or analytics. Bookmarks, filters and your additions live in your own browser (`localStorage`).

---

## Contents

1. [How it works](#how-it-works)
2. [Run it on your computer](#run-it-on-your-computer)
3. [Put it online with GitHub Pages](#put-it-online-with-github-pages)
4. [Add your Kaggle key as a GitHub Secret](#add-your-kaggle-key-as-a-github-secret)
5. [Add your own opportunities](#add-your-own-opportunities)
6. [Add a new source](#add-a-new-source)
7. [Change fields and keywords](#change-fields-and-keywords)
8. [Sources: used and skipped](#sources-used-and-skipped)
9. [Data schema](#data-schema)
10. [Troubleshooting](#troubleshooting)

---

## How it works

```
 every 6 h (GitHub Actions)
          │
          ▼
 scraper/update.py ──► each source in scraper/sources/ (one small file each)
          │               │ public JSON APIs / RSS feeds, robots.txt checked first
          │               ▼
          │           normalise → tag fields by keyword → merge data/custom.json
          │           → drop expired → remove duplicates → sort
          ▼
 data/opportunities.json  ──commit──►  GitHub Pages  ──►  index.html reads it
```

```
.
├── index.html                  the page
├── assets/
│   ├── css/styles.css          all styling (light + dark)
│   ├── js/app.js               state, filters, tabs, sorting, start-up
│   ├── js/render.js            cards, loading and empty states
│   ├── js/form.js              "Add opportunity" dialog + Export JSON
│   ├── js/utils.js             dates, countdowns, localStorage helpers
│   └── favicon.svg
├── data/
│   ├── opportunities.json      written by the scraper (don't edit by hand)
│   └── custom.json             YOUR entries (edit freely)
├── scraper/
│   ├── update.py               main script
│   ├── config.py               keywords, sources on/off, search terms
│   ├── helpers.py              HTTP + robots.txt, dates, tagging, make_item()
│   ├── requirements.txt        requests, beautifulsoup4, feedparser
│   └── sources/                one file per source
└── .github/workflows/update.yml
```

**Rules the scraper follows**

- **Polite:** checks `robots.txt` before every request (with proper `*` wildcard support), waits 1 s between requests to the same site, and identifies itself honestly as `OpportunityRadarBot`.
- **Never crashes because of one site.** If a source fails or blocks us, it logs a warning and keeps that source's items from the last run.
- **Expiry:** an item is dropped once its deadline has passed. With no deadline, it's dropped once its end date has passed. Scraped items with no dates at all are dropped 60 days after first being seen. The page also hides expired items itself, so nothing stale shows between runs.
- **Duplicates:** the same URL, or the same title with the same start date, counts as one opportunity. Your `custom.json` copy wins, then verified sources, then the most complete copy.
- **Deadlines for events:** TeSS/EMBL-EBI, Galaxy and nf-core events and MLH hackathons don't publish a registration deadline, so their **start date** is used (you must register by then at the latest). Ongoing courses show "Ongoing · until …" instead.
- **Spotting webinars:** titles with "webinar", "bytesize", "live session" and similar words count as webinars. So do online events called a talk, seminar or lecture (in person they don't), and online TeSS/EMBL-EBI sessions that start and end on the same day without being called a course or workshop. The rules live in `_TYPE_RULES` in `scraper/helpers.py`.

---

## Run it on your computer

You need Python 3.10+ (you have 3.12).

```bash
python -m venv .venv
```

Activate it. On Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

On macOS/Linux: `source .venv/bin/activate`. Then:

```bash
pip install -r scraper/requirements.txt
```

```bash
python scraper/update.py
```

You'll see a summary like:

```
================ SUMMARY ================
source        status     items
mlh           ok            24
unstop        ok            66
...
kaggle        skipped        0
-----------------------------------------
open opportunities written : 203
new since last run         : 12
removed (deadline passed)  : 3
removed (no longer listed) : 1
failed / blocked sources   : biotecnika
```

Now serve the site. Opening `index.html` by double-clicking won't work, because browsers block loading the JSON from a `file://` page.

```bash
python -m http.server 8000
```

Open <http://localhost:8000>.

Other useful commands:

```bash
python scraper/update.py --only tess
```

```bash
python scraper/update.py --custom-only
```

`--only NAME` re-fetches a single source and keeps the others' data. `--custom-only` doesn't touch the internet: it re-merges `custom.json` into the existing data.

---

## Put it online with GitHub Pages

1. **Create a repository** on GitHub, e.g. `opportunity-radar`. It must be **public** for free GitHub Pages. That means `custom.json` is public too, so don't put anything private in it.
2. **Push this folder** (from the project folder):

   ```bash
   git init -b main
   ```

   ```bash
   git add . && git commit -m "Opportunity Radar"
   ```

   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/opportunity-radar.git
   ```

   ```bash
   git push -u origin main
   ```

3. In the repo on GitHub, open **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. Open the **Actions** tab, click **Update opportunities**, then **Run workflow**. In a minute or two your site is live at `https://YOUR-USERNAME.github.io/opportunity-radar/`. The link is also shown on the workflow run's *deploy* step.

From then on it updates itself every 6 hours (at :17 past 0, 6, 12 and 18 UTC, which is 05:47, 11:47, 17:47 and 23:47 in India). GitHub sometimes runs scheduled jobs a little late. To update right now, press **Run workflow** again.

Every push you make to `main` (say, a change to `custom.json` or the page) also republishes the site. Those runs skip the scraping, so they're quick.

---

## Add your Kaggle key as a GitHub Secret

The Kaggle source uses Kaggle's official API, which needs your credentials. **Never commit the key to the repo**; `kaggle.json` is already in `.gitignore`.

1. Sign in at kaggle.com → click your profile picture → **Settings** → **API** → **Create New Token**. This downloads `kaggle.json`, which looks like `{"username":"yourname","key":"abc123..."}`.
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**. Add two secrets:
   - Name `KAGGLE_USERNAME`, value: the `username` from the file
   - Name `KAGGLE_KEY`, value: the `key` from the file
3. Run the workflow. The summary should now show `kaggle  ok`.

If Kaggle gives you a newer single **API token** instead, add it as one secret named `KAGGLE_API_TOKEN`.

For local runs, put `kaggle.json` in `~/.kaggle/` (on Windows `C:\Users\YOU\.kaggle\`) and the scraper picks it up automatically.

---

## Add your own opportunities

**Option A: edit `data/custom.json`** (best for things you want everywhere). Add an object to the `items` list:

```json
{
  "id": "custom-embo-singlecell-2027",
  "title": "EMBO Practical Course: Single-Cell Omics 2027",
  "organiser": "EMBO",
  "type": "workshop",
  "fields": ["single-cell", "transcriptomics"],
  "mode": "offline",
  "location": "Heidelberg, Germany",
  "region": "International",
  "start_date": "2027-05-10",
  "end_date": "2027-05-17",
  "deadline": "2027-02-01",
  "stipend_or_prize": "Travel bursaries available",
  "eligibility": "PhD students and postdocs; some UG places",
  "url": "https://example.org/course",
  "notes": ""
}
```

Only `title`, `type` and `url` are required. Leave unknown dates as `null`. For programmes whose dates aren't announced yet, set `"expected": true` and the card shows "Dates expected". Commit and push: the page reads `custom.json` directly, so the change shows up as soon as GitHub Pages republishes, about a minute later.

Mind the JSON commas: every object except the last one in the list needs a `,` after its closing `}`. If the file is invalid, `update.py` tells you the line number.

**Option B: the "+ Add" button on the site.** It saves to your browser only, with validation. Your entries appear under **My additions** with Edit and Delete. To make them permanent, click **Export JSON** in the dialog, paste the snippet into `custom.json` as described in the dialog, commit, and then delete the browser copies.

---

## Add a new source

Each source is a small file in `scraper/sources/` with one function, `fetch_items()`, that returns a list of items built with `make_item()`.

1. **Check the site first:**
   - Does it have an API, a JSON endpoint or an RSS feed? Use that. For WordPress sites, try `https://site/feed/` or `https://site/category/NAME/feed/`.
   - Read `https://site/robots.txt`. The scraper enforces it anyway, but there's no point writing code for a blocked path.
   - Read the site's **Terms of Use** for words like "scrape", "crawl", "robot". If they forbid it, add the site to `MANUAL_SOURCES` in `config.py` instead.
2. **Create `scraper/sources/mysite.py`** (copy `hackerearth.py`, the smallest one):

   ```python
   """MySite - what it lists, and how we read it (API / RSS)."""
   from helpers import fetch, make_item

   NAME = "mysite"

   def fetch_items():
       data = fetch("https://mysite.org/api/events", params={"status": "open"})
       items = []
       for ev in data["events"]:
           item = make_item(
               source=NAME,
               title=ev["name"],
               url=ev["link"],
               type="workshop",          # one of the 8 types
               mode="online",            # online | offline | hybrid
               organiser=ev.get("host", ""),
               start_date=ev.get("start"),
               deadline=ev.get("register_by"),
               tag_text=ev.get("description", ""),   # used for field tagging
               bio_source=True,          # True if the site is biology-only
           )
           if item:
               items.append(item)
       return items
   ```

   For RSS: `feed = feedparser.parse(fetch(URL, kind="bytes"))`, then loop over `feed.entries` (see `dream.py`). For an HTML page: `fetch(URL, kind="text")` plus BeautifulSoup (see `mlh.py`).
3. **Register it** in `scraper/sources/__init__.py` (import it and add `"mysite": mysite.fetch_items`) and add `"mysite": True` to `ENABLED_SOURCES` in `config.py`.
4. **Test it:** `python scraper/update.py --only mysite`
5. Optional: add `"mysite": "MySite"` to `SOURCE_NAMES` in `assets/js/render.js` for a nicer label, and add it to `VERIFIED_SOURCES` in `config.py` if it's the organiser's own site.

To **remove** a source, set it to `False` in `ENABLED_SOURCES`.

---

## Change fields and keywords

Open `scraper/config.py`:

- `FIELD_KEYWORDS`: each field tag and the keywords that trigger it. `genom*` matches genome, genomics and genomic. Plain words match whole words only, so `ml` doesn't match "html".
- `KEEP_GENERAL_ITEMS`: whether general hackathons with no matching keyword are kept (tagged `general`) or dropped.
- `UNSTOP_SEARCH_TERMS`, `TESS_QUERIES`, `BIOTECNIKA_FEEDS`: what to search for.
- `MANUAL_SOURCES`: the "Check manually" links in the sidebar.

You can also add a field from the sidebar's **Add a field** box. That saves it in your browser, so you can tag your own additions with it.

---

## Sources: used and skipped

All were tested on 20 Nov 2026.

| Source | Status | How |
|---|---|---|
| MLH | ✅ used | Season events page. The event list is embedded as JSON in the page; the official API needs a login |
| Unstop | ✅ used | Public JSON API (robots.txt explicitly allows `/api/public/*`). Hackathons + keyword searches for internships, competitions and workshops. Search results are judged on the role itself (title, skills), and sales/HR/marketing roles are dropped. Unstop has very few biology internships, so most of its internships are data science / ML |
| HackerEarth | ✅ used | Public JSON endpoint (usually only a few items) |
| Devfolio | ✅ used | Public JSON API (participant data is never stored) |
| Kaggle | ✅ used, needs key | Official API; skipped with a warning until you add the secret. *Not yet tested with a real key* |
| DREAM Challenges | ✅ used | WordPress RSS; only posts tagged "Open Challenge" or "Pre-Register" |
| EMBL-EBI training | ✅ used | Via the TeSS API, filtered to EMBL-EBI (EBI Search returned empty titles) |
| TeSS (ELIXIR) | ✅ used | Open JSON API: keyword searches, plus its online events (the main webinar source; kept only if they match your fields); stands in for "related RSS feeds" |
| Galaxy Project | ✅ used | Public events RSS (workshops, hackathons, conferences, occasional webinars); non-bio topics skipped via `GALAXY_SKIP_PATTERN` |
| nf-core | ✅ used | Public events RSS: "bytesize" webinars, hackathons, training (only upcoming ones are kept) |
| NCBI Insights | ✅ used | NCBI's blog RSS, filtered to webinar/codeathon/workshop posts that mention a future date. Often 0 items between announcements |
| EMBL events | ✅ used | Public events page with machine-readable attributes: EMBL courses, EMBO Workshops/conferences and webinars (Heidelberg, EMBL-EBI, Barcelona, Rome, virtual). Events with closed registration are skipped |
| Opportunities For Youth | ✅ used | WordPress RSS (several pages). All fields, so only science-matched posts that are clearly an internship/fellowship/summer school/conference/competition are kept |
| Opportunity Desk | ✅ used | WordPress category RSS (internships, fellowships, training), same filtering. Its terms have no rule against reading feeds |
| Zindi | ✅ used | Public JSON API of open ML/data-science competitions |
| Biotecnika | ⚠️ often blocked | WordPress category RSS. The site sits behind a Cloudflare bot check that often answers HTTP 403. We respect that: on the first block it stops, warns, and keeps the last good data. No workarounds |
| Devpost | ❌ skipped | Its Terms of Use forbid automated scraping and crawling (even though robots.txt allows it) |
| Internshala | ❌ skipped | Its Terms forbid bots and scrapers; robots.txt blocks search pages |
| ISCB events | ❌ skipped | The calendar app's robots.txt is `Disallow: /`; the main site's RSS feed is empty |
| Bioinformatics.org | ❌ skipped | No working RSS or API; the jobs board is mostly postdoc roles |
| CAFA | ➖ covered | No feed of its own; recent rounds ran on Kaggle |
| iGEM | ❌ skipped | One competition a year, no feed. Add it to `custom.json` |
| IndiaBioscience | ❌ skipped | Answers automated requests with HTTP 403 (listed under "Check manually") |
| AICTE Internship Portal | ❌ skipped | Its terms forbid collecting data by automated means |
| IASc Lecture Workshops | ❌ skipped | The server cuts the page off before the list arrives |
| NCBS, Codabench | ❌ skipped | Anti-bot challenge pages |
| Wellcome Connecting Science, ICGEB | ❌ skipped | Refuse automated connections |
| Grand Challenge | ❌ skipped | robots.txt disallows its API |
| LinkedIn, Naukri, Indeed, Glassdoor | ❌ not attempted | Their terms forbid scraping |

**Annual programmes in `custom.json`.** Big internship programmes (IIT summer programmes, JNCASR, TIFR, RIKEN, Weizmann, NUS Amgen, OIST, KAUST, Vienna BioCenter…) don't have feeds, so they live in `data/custom.json` with their official links. Where the 2027 call isn't out yet they're marked `"expected": true` and the note says what last year's deadline was. When a call opens, edit the entry: set the `deadline` and remove `expected`.

Skipped sites appear under **Check manually** in the sidebar. **Source status** in the sidebar shows how each source did in the last run.

---

## Data schema

Every item in `opportunities.json` (and `custom.json`):

| Field | Example | Notes |
|---|---|---|
| `id` | `"custom-riken-cbs-summer-2027"` | unique, stable |
| `title` | `"RIKEN CBS Summer Program 2027"` | |
| `organiser` | `"RIKEN Center for Brain Science"` | |
| `type` | `"internship"` | hackathon, internship, fellowship, competition, conference, workshop, webinar, summer-school |
| `fields` | `["neuroscience"]` | tags from `FIELD_KEYWORDS` |
| `mode` | `"offline"` | online, offline, hybrid |
| `location` | `"Wako, Japan"` | |
| `region` | `"International"` | India, International, Online |
| `start_date` / `end_date` / `deadline` | `"2027-01-08"` | `YYYY-MM-DD` or `null` |
| `stipend_or_prize` | `"₹15,000/month"` | free text |
| `eligibility` | `"UG students"` | free text |
| `url` | `"https://…"` | |
| `source` | `"tess"` | which source it came from (`custom` for yours) |
| `date_added` | `"2026-11-20"` | first time the scraper saw it |
| `verified` | `true` | from the organiser/platform itself, or your own list |
| `notes` *(optional)* | `"Applications open 20 Dec"` | |
| `expected` *(optional)* | `true` | dates not announced yet |

---

## Troubleshooting

- **The page says it couldn't load the data.** You opened `index.html` as a file. Run `python -m http.server 8000` and use <http://localhost:8000>.
- **"Updated 3 days ago" in orange.** The scheduled job hasn't run. GitHub pauses schedules in repos with no activity for 60 days; the bot's commits usually count as activity, but if you get an email saying the workflow was disabled, re-enable it in the Actions tab.
- **The workflow fails at "Commit updated data" with a permission error.** Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**.
- **The deploy job fails.** Check that **Settings → Pages → Source** is set to **GitHub Actions**.
- **A source shows `failed` or `blocked`.** Open the latest run in the Actions tab; the log shows the error and the summary. Sites change their APIs: the fix is usually a field name in that source's file. Its old items are kept meanwhile.
- **A field tag looks wrong.** Adjust the keywords in `config.py`. Stems like `neuro*` can over-match, and very common words make a tag meaningless.

Always double-check dates and eligibility on the official page before applying. The scraper is a radar, not the source of truth.
