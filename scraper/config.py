"""
config.py - everything you are likely to want to tweak lives here.

This is a plain Python file (not JSON) so it can have comments.
After editing it, run `python scraper/update.py` locally to check nothing broke.
"""

# ---------------------------------------------------------------------------
# 1. Which sources run
# ---------------------------------------------------------------------------
# Set a source to False to switch it off without deleting any code.
# The names must match the keys in scraper/sources/__init__.py.
ENABLED_SOURCES = {
    "mlh": True,
    "unstop": True,
    "hackerearth": True,
    "devfolio": True,
    "kaggle": True,        # needs KAGGLE_USERNAME + KAGGLE_KEY (or KAGGLE_API_TOKEN)
    "dream": True,
    "embl_ebi": True,
    "tess": True,
    "galaxy": True,
    "nfcore": True,
    "ncbi": True,
    "embl": True,
    "ofy": True,
    "opportunitydesk": True,
    "zindi": True,
    "biotecnika": True,
}

# ---------------------------------------------------------------------------
# 2. Field tags (keyword matching)
# ---------------------------------------------------------------------------
# Each key is a field tag shown in the UI. Each value is a list of keywords.
# An item gets a tag if ANY keyword appears in its title/description/themes.
#
# Matching rules (see helpers.match_fields):
#   - case-insensitive
#   - whole words only:  "ml" matches "ML" but not "html"
#   - end a keyword with * to match a word prefix: "genom*" matches
#     genome, genomes, genomic, genomics
#
# To add a new field: add a new line like
#     "ecology": ["ecology", "biodiversity", "ecosystem*"],
FIELD_KEYWORDS = {
    "bioinformatics": [
        # (avoid words like "blast" or "galaxy": they match "have a blast"
        #  or "Samsung Galaxy" in hackathon descriptions)
        "bioinformatic*", "sequence analysis", "biostatistic*", "biocuration",
        "biocurator", "nextflow", "snakemake",
    ],
    "computational-biology": [
        "computational biology", "comp bio", "compbio", "biocomputing",
        "in silico", "mathematical biology", "biophysic*", "computational biolog*",
    ],
    "systems-biology": [
        "systems biology", "network biology", "metabolic model*", "kinetic model*",
    ],
    "genomics": [
        "genom*", "dna", "ngs", "sequencing", "gwas", "variant calling",
        "exome", "metagenom*", "genetic*", "crispr",
    ],
    "single-cell": [
        "single-cell", "single cell", "scrna*", "scrna-seq", "snrna*",
        "spatial transcriptomic*", "spatial omics", "cell atlas", "cell map",
    ],
    "transcriptomics": [
        "transcriptom*", "rna-seq", "rnaseq", "gene expression", "rna sequencing",
    ],
    "multi-omics": [
        "multi-omics", "multiomics", "multi omics", "proteom*", "metabolom*",
        "epigenom*", "lipidom*", "omics",
    ],
    "protein": [
        "protein*", "alphafold", "structural biology", "molecular dynamics",
        "docking", "enzyme*", "antibod*", "structure prediction",
    ],
    "drug-discovery": [
        "drug discovery", "drug design", "drug development", "cheminformatic*",
        "molecul*", "pharma*", "admet", "small molecule*", "target 2035",
    ],
    "neuroscience": [
        "neuroscien*", "neurobiolog*", "brain", "neuron*", "neurolog*",
        "neuroimaging", "eeg", "connectom*", "alzheimer*", "parkinson*",
    ],
    "healthcare-ai": [
        "healthcare", "health tech", "healthtech", "medical", "medicine",
        "clinical", "diagnos*", "radiolog*", "patient*", "biomedical",
        "medtech", "hospital*", "disease*",
    ],
    "biotech": [
        "biotech*", "bioengineering", "bio-engineering", "synthetic biology",
        "igem", "life science*", "biology", "biological", "microbiolog*",
        "molecular biology", "bioprocess*", "biomedical engineering", "bio",
    ],
    "ml-ai": [
        "machine learning", "deep learning", "artificial intelligence", "ai",
        "ml", "llm*", "data science", "neural network*", "computer vision",
        "nlp", "generative ai", "genai",
    ],
}

# Only the title plus this many characters of description/themes are used
# for tagging. Long descriptions mention everything ("disease", "AI", ...)
# and would give every item five tags.
TAG_TEXT_MAX_CHARS = 600

# Items from bio-specific sources (TeSS, EMBL-EBI, DREAM, Biotecnika) that
# match no keyword still get this tag, so they never show up untagged.
BIO_FALLBACK_FIELD = "biotech"

# Items from general sources (hackathon sites, Kaggle) that match no keyword:
#   True  -> keep them, tagged "general" (you can hide them with the field filter)
#   False -> drop them entirely, so only field-relevant items are kept
KEEP_GENERAL_ITEMS = True
GENERAL_FIELD = "general"

# ---------------------------------------------------------------------------
# 3. Per-source settings
# ---------------------------------------------------------------------------

# Unstop: search terms are run for each opportunity type listed.
# Hackathons are fetched without a search term (general list, first N pages).
UNSTOP_HACKATHON_PAGES = 2          # 30 items per page
UNSTOP_SEARCH_TYPES = ["internships", "competitions", "workshops"]
# Unstop has very few biology listings (a "bioinformatics" internship search
# returned 1 result when tested), so the search also covers neighbouring
# areas such as data science and research. Results are still only kept if
# they match one of your field keywords.
UNSTOP_SEARCH_TERMS = [
    "bioinformatics", "computational biology", "biotech", "genomics",
    "biology", "healthcare", "drug discovery", "neuroscience",
    "life sciences", "research", "data science", "machine learning",
    "pharma", "medical",
]

# TeSS (ELIXIR training portal) keyword searches.
TESS_QUERIES = [
    "bioinformatics", "computational biology", "single-cell", "genomics",
    "transcriptomics", "multi-omics", "systems biology", "neuroscience",
    "drug discovery", "machine learning", "protein structure",
    "RNA-seq", "metagenomics", "proteomics", "structural biology",
    "python", "R programming", "statistics", "data science",
    "artificial intelligence", "cancer", "immunology", "microbiology",
    "epidemiology", "imaging", "summer school", "spatial",
]
TESS_PER_QUERY = 30                 # results per query (TeSS max is 100)
TESS_ONLINE_PAGES = 3               # pages of 100 online events (where webinars are)

# Opportunities For Youth and Opportunity Desk post opportunities in every
# field (policy, journalism, business...). Only posts that match one of your
# field keywords (other than ML/AI on its own) and look like one of our types
# are kept. More pages = more history, each page is 10 posts.
OFY_PAGES = 4
OPPORTUNITYDESK_FEEDS = {           # category slug -> pages to read
    "internships": 3,
    "fellowships": 3,
    "training": 2,
}

# Galaxy events about these (non-life-science) topics are skipped.
GALAXY_SKIP_PATTERN = r"humanities|astronom|astrophysic|climate|earth system|material science"

# NCBI Insights blog: only posts whose title matches this are kept.
NCBI_TITLE_PATTERN = r"webinar|codeathon|workshop|training|virtual|office hours|tutorial"

# Biotecnika WordPress category feeds (slug -> default opportunity type).
# Find more slugs at https://www.biotecnika.org/wp-json/wp/v2/categories?search=WORD
# ("fellowship" exists too, but its feed returned HTTP 403 when tested.)
BIOTECNIKA_FEEDS = {
    "summer-training-internship": "internship",
    "biotech-internships-projects": "internship",
    "workshop": "workshop",
    "training": "workshop",
}
BIOTECNIKA_MAX_AGE_DAYS = 45        # ignore posts older than this

# Kaggle: how many pages of active competitions to read (20 per page).
KAGGLE_PAGES = 2

# ---------------------------------------------------------------------------
# 4. Cleaning rules
# ---------------------------------------------------------------------------

# Scraped items with NO deadline, start or end date are dropped this many
# days after they were first seen (so stale posts don't pile up).
# Items in custom.json are never auto-dropped for missing dates.
UNDATED_ITEM_MAX_DAYS = 60

# Used to decide region = "India" when the location text mentions any of these.
INDIA_PLACES = [
    "india", "pune", "mumbai", "delhi", "new delhi", "bengaluru", "bangalore",
    "hyderabad", "chennai", "kolkata", "ahmedabad", "gandhinagar", "noida",
    "gurgaon", "gurugram", "jaipur", "lucknow", "bhopal", "indore", "kochi",
    "trivandrum", "thiruvananthapuram", "chandigarh", "mohali", "bhubaneswar",
    "guwahati", "kanpur", "kharagpur", "roorkee", "vellore", "manipal",
    "mysuru", "mysore", "nagpur", "surat", "vadodara", "coimbatore",
    "visakhapatnam", "patna", "ranchi", "dehradun", "goa", "maharashtra",
    "karnataka", "tamil nadu", "kerala", "telangana", "gujarat", "rajasthan",
    "uttar pradesh", "west bengal", "odisha", "assam", "punjab", "haryana",
    "iit", "iisc", "iiser", "nit", "aiims",
]

# Sources whose listings come straight from the organiser or the platform you
# apply on, so items from them are marked verified=true. Aggregators and news
# sites (TeSS, Biotecnika) are not. Items in custom.json are always verified.
VERIFIED_SOURCES = {"mlh", "unstop", "hackerearth", "devfolio", "kaggle", "dream", "embl_ebi",
                    "galaxy", "nfcore", "ncbi", "embl", "zindi"}

# All dates are interpreted in India time (UTC+5:30), see helpers.IST.

# ---------------------------------------------------------------------------
# 5. "Check manually" links shown in the sidebar
# ---------------------------------------------------------------------------
# Sources we deliberately do NOT scrape (terms of service or robots.txt say no),
# plus anything else you like to browse by hand.
MANUAL_SOURCES = [
    {"name": "Devpost hackathons", "url": "https://devpost.com/hackathons",
     "why": "Terms of Use forbid scraping"},
    {"name": "Internshala: bioinformatics", "url": "https://internshala.com/internships/bioinformatics-internship",
     "why": "Terms forbid bots"},
    {"name": "ISCB events calendar", "url": "https://www.iscb.org/conferences-events/events-calendar",
     "why": "robots.txt blocks bots"},
    {"name": "iGEM competition", "url": "https://competition.igem.org/",
     "why": "Once a year, no feed"},
    {"name": "Bioinformatics.org jobs", "url": "https://www.bioinformatics.org/jobs/",
     "why": "No feed or API"},
    {"name": "CAFA (protein function)", "url": "https://biofunctionprediction.org/cafa/",
     "why": "Rounds run on Kaggle"},
    {"name": "IndiaBioscience events & webinars", "url": "https://indiabioscience.org/events",
     "why": "Blocks automated access"},
    {"name": "AICTE Internship Portal", "url": "https://internship.aicte-india.org/",
     "why": "Terms forbid automated collection"},
    {"name": "IASc Lecture Workshops (India)", "url": "https://webjapps.ias.ac.in/SEP/lecture_workshop_futhcoming.jsp",
     "why": "Page can't be read automatically"},
    {"name": "NCBS events", "url": "https://www.ncbs.res.in/events",
     "why": "Anti-bot check"},
    {"name": "Wellcome Connecting Science courses", "url": "https://coursesandconferences.wellcomeconnectingscience.org/",
     "why": "Refuses automated connections"},
    {"name": "ICGEB courses & fellowships", "url": "https://www.icgeb.org/",
     "why": "Refuses automated connections"},
    {"name": "Grand Challenge (medical imaging)", "url": "https://grand-challenge.org/challenges/",
     "why": "robots.txt blocks its API"},
]

# ---------------------------------------------------------------------------
# 6. HTTP politeness
# ---------------------------------------------------------------------------
# The standard bot format ("Mozilla/5.0 (compatible; Name/version; info)"),
# the same shape Googlebot uses. It still says honestly that we're a bot;
# some site firewalls reject user agents that don't start with "Mozilla/5.0".
USER_AGENT = (
    "Mozilla/5.0 (compatible; OpportunityRadarBot/1.0; "
    "personal non-commercial dashboard, runs every 6 hours)"
)
REQUEST_TIMEOUT = 25                # seconds
DELAY_BETWEEN_REQUESTS = 1.0        # seconds, per website
