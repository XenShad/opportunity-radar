"""
EMBL-EBI training - courses, webinars and workshops from the European
Bioinformatics Institute (UniProt, AlphaFold, Ensembl, single-cell, ...).

How: EMBL-EBI publishes its training events to TeSS, so we ask the TeSS JSON
API for events from that content provider. (EBI Search also has a training
domain, but its titles came back empty when tested; TeSS's data is cleaner.)
"""

from helpers import fetch
from sources.tess import API, event_to_item

NAME = "embl_ebi"
PROVIDER = "European Bioinformatics Institute (EBI)"


def fetch_items():
    events = fetch(API, params={"content_provider": PROVIDER, "per_page": 100})
    items = []
    for ev in events:
        item = event_to_item(ev, NAME)
        if item:
            items.append(item)
    return items
