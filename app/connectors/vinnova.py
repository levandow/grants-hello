from __future__ import annotations
import os, datetime as dt, requests
from typing import Iterable, Dict, Any

VINNOVA_BASE = "https://data.vinnova.se/api/ansokningsomgangar"
VINNOVA_SINCE = os.getenv("VINNOVA_SINCE", "2024-01-01")

def _since_date() -> str:
    try:
        dt.date.fromisoformat(VINNOVA_SINCE)
        return VINNOVA_SINCE
    except Exception:
        return "2024-01-01"

def fetch() -> Iterable[Dict[str, Any]]:
    """Fetches raw Vinnova 'Utlysningar' records as JSON dicts"""
    url = f"{VINNOVA_BASE}/{_since_date()}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json() or []