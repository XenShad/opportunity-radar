"""
The list of all sources.

To ADD a source:
  1. Create scraper/sources/mysite.py with a fetch_items() function that
     returns a list of dicts built with helpers.make_item(...)
     (copy a small one like hackerearth.py as a template).
  2. Import it below and add it to SOURCES.
  3. Add "mysite": True to ENABLED_SOURCES in config.py.

To REMOVE a source: set it to False in config.ENABLED_SOURCES (or delete it here).
"""

from sources import (biotecnika, devfolio, dream, embl_ebi, galaxy, hackerearth,
                     kaggle, mlh, ncbi, nfcore, tess, unstop)

# name -> function that returns a list of items
SOURCES = {
    "mlh": mlh.fetch_items,
    "unstop": unstop.fetch_items,
    "hackerearth": hackerearth.fetch_items,
    "devfolio": devfolio.fetch_items,
    "kaggle": kaggle.fetch_items,
    "dream": dream.fetch_items,
    "embl_ebi": embl_ebi.fetch_items,
    "tess": tess.fetch_items,
    "galaxy": galaxy.fetch_items,
    "nfcore": nfcore.fetch_items,
    "ncbi": ncbi.fetch_items,
    "biotecnika": biotecnika.fetch_items,
}
