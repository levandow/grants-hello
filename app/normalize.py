from datetime import datetime
from typing import Dict, Any, List
from jsonschema import validate, ValidationError
import json
from pathlib import Path

# Load JSON Schema once
_SCHEMA = json.loads(Path("packages/schema/opportunity.schema.json").read_text(encoding="utf-8"))

def _iso_date(s: str | None) -> str | None:
    if not s:
        return None
    # Accept common formats; return YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # fallback untouched; schema will catch if invalid

def normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize minimal fields: dates, title/summary dicts, status mapping."""
    out = {**record}

    # Ensure title/summary structure
    out["title"] = out.get("title") or {}
    out["title"].setdefault("sv", None)
    out["title"].setdefault("en", None)

    out["summary"] = out.get("summary") or {}
    out["summary"].setdefault("sv", None)
    out["summary"].setdefault("en", None)

    # Dates
    out["opens_at"]  = _iso_date(out.get("opens_at"))
    out["closes_at"] = _iso_date(out.get("closes_at"))
    if isinstance(out.get("deadlines"), list):
        norm_dl: List[Dict[str, Any]] = []
        for d in out["deadlines"]:
            nd = dict(d)
            nd["date"] = _iso_date(d.get("date"))
            norm_dl.append(nd)
        out["deadlines"] = norm_dl

    # Status mapping examples
    status = (out.get("status") or "").lower().strip()
    status_map = {
        "forthcoming": "planned", "upcoming": "planned",
        "open": "open", "active": "open",
        "closed": "closed", "deadline passed": "closed"
    }
    out["status"] = status_map.get(status, status if status in {"open","planned","closed"} else "open")

    # Minimal links
    links = out.get("links") or {}
    if "landing" not in links:
        links["landing"] = ""
    out["links"] = links

    # Validate
    try:
        validate(out, _SCHEMA)
    except ValidationError as e:
        # Make validation errors readable during development
        raise ValueError(f"Schema validation error at {list(e.path)}: {e.message}") from e

    return out
