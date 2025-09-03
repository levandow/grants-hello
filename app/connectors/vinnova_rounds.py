# app/connectors/vinnova_rounds.py
from __future__ import annotations
import os, datetime as dt, requests
from typing import Iterable, Dict, Any, Optional

BASE = "https://data.vinnova.se/api/ansokningsomgangar"
VINNOVA_SINCE = os.getenv("VINNOVA_SINCE", "2024-01-01")

def _since() -> str:
    try:
        dt.date.fromisoformat(VINNOVA_SINCE)
        return VINNOVA_SINCE
    except Exception:
        return "2024-01-01"

def fetch(page_size: int = 200, max_pages: int = 50) -> Iterable[Dict[str, Any]]:
    """
    The endpoint commonly supports incremental by date, sometimes with simple pagination.
    We try date-first; if the API doesn’t page, we’ll just return the whole list.
    """
    url = f"{BASE}/{_since()}"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        for x in data:
            yield x
        return
    # If the API returns an object with results/pagination, handle it:
    items = (data.get("results") or data.get("Result") or data.get("data") or [])
    for x in items:
        yield x
