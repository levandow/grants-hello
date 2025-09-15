# app/connectors/eu_ftop.py
from __future__ import annotations
import requests
from typing import Iterable, Dict, Any

API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY = "SEDIA"
api_text = "***"

# Filters: open grant calls under Horizon Europe (43108390), status OPEN (31094502)
# See examples in public threads and EC pages; adjust as needed.
QUERY = {
    "bool": {
        "must": [
            {"terms": {"type": ["1", "2"]}},              # calls/topics
            {"terms": {"status": ["31094502"]}},          # OPEN
            {"term": {"programmePeriod": "2021 - 2027"}}, # Horizon Europe period
            {"terms": {"frameworkProgramme": ["43108390"]}}
        ]
    }
}
SORT = {"field": "sortStatus", "order": "ASC"}

def _payload(page: int, size: int) -> Dict[str, Any]:
    return {
        "query": QUERY,
        "sort": [SORT],
        "pageNumber": page,
        "pageSize": size,
        "languages": ["en"],
        # Request all available fields to capture full metadata
        "fields": ["*"],
    }

def fetch(page_size: int = 50, max_pages: int = 10) -> Iterable[Dict[str, Any]]:
    for page in range(1, max_pages + 1):
        r = requests.post(
            f"{API}?apiKey={API_KEY}&text={api_text}",
            json=_payload(page, page_size),
            timeout=40,
        )
        r.raise_for_status()
        data = r.json()

        items: list[Any] = []
        if isinstance(data, dict):
            if isinstance(data.get("results"), list):
                items = data["results"]
            else:
                # Some responses wrap the actual hits inside ``resultList``
                rl = data.get("resultList")
                if isinstance(rl, dict):
                    if isinstance(rl.get("results"), list):
                        items = rl["results"]
                    elif isinstance(rl.get("result"), list):
                        items = rl["result"]

        if not items:
            break
        for rec in items:
            yield rec
