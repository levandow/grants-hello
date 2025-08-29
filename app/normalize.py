from datetime import datetime
from typing import Dict, Any, List
from jsonschema import validate, ValidationError
import json
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional

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

# app/normalize.py (only the function below)

def _iso_or_none(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = str(v).strip()
    # try common formats, normalize to YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    if v.isdigit() and len(v) == 8:
        try:
            return datetime.strptime(v, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def _status_from_dates(opens_at: Optional[str], closes_at: Optional[str]) -> str:
    today = date.today()
    if opens_at:
        try:
            if date.fromisoformat(opens_at) > today:
                return "planned"
        except Exception:
            pass
    if closes_at:
        try:
            return "closed" if date.fromisoformat(closes_at) < today else "open"
        except Exception:
            pass
    return "open"

def _extract_link(obj: Any) -> str:
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        for k in ("URL", "Url", "url", "HRef", "href", "link"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""

def normalize_vinnova(u: dict) -> dict:
    # IDs
    dnr = (u.get("Diarienummer") or u.get("DiarienummerUtlysning") or "").strip()
    uid = dnr or f"vno-{abs(hash((u.get('Titel') or u.get('TitelEngelska') or '').lower()))}"

    # Titles
    title_sv = (u.get("Titel") or "").strip() or None
    title_en = (u.get("TitelEngelska") or "").strip() or None

    # Summary: prefer first WebText paragraph; fallback to Beskrivning fields
    summary_sv = None
    summary_en = None
    webtexts = u.get("WebTextLista") or []
    if isinstance(webtexts, list) and webtexts:
        w0 = webtexts[0] or {}
        summary_sv = (w0.get("TextSv") or "").strip() or None
        summary_en = (w0.get("TextEn") or "").strip() or None
    if not summary_sv:
        summary_sv = (u.get("Beskrivning") or "").strip() or None
    if not summary_en:
        summary_en = (u.get("BeskrivningEngelska") or "").strip() or None

    # Programme: infer Innovair if in title
    programme = "Innovair" if (title_sv or title_en or "").lower().__contains__("innovair") else None

    # Links: landing = first in LankLista; guidelines = Primary document
    links: Dict[str, str] = {}
    for item in (u.get("LankLista") or []):
        url = _extract_link(item)
        if url:
            links["landing"] = url
            break
    if not links.get("landing"):
        links["landing"] = ""  # schema requires string

    for doc in (u.get("DokumentLista") or []):
        if doc.get("Primary"):
            links["guidelines"] = doc.get("fileURL") or ""
            break

    # Dates
    opens_at  = _iso_or_none(u.get("Oppningsdatum") or u.get("Öppningsdatum") or u.get("OpeningDate"))
    closes_at = _iso_or_none(u.get("Stangningsdatum") or u.get("Stängningsdatum") or u.get("ClosingDate"))

    deadlines: List[Dict[str, Any]] = []
    if closes_at:
        deadlines.append({"type": "single", "date": closes_at})

    # Status from dates
    status = _status_from_dates(opens_at, closes_at)

    # Tags (light heuristic)
    tags = ["sweden", "public-funder"]
    text_blob = " ".join(filter(None, [title_sv, title_en, summary_sv, summary_en])).lower()
    if "flyg" in text_blob or "aero" in text_blob or "air" in text_blob:
        tags.append("aviation")
    if "smf" in text_blob or "sme" in text_blob:
        tags.append("sme")

    # Contacts to notes (since schema lacks a contacts field)
    notes = None
    contacts = u.get("KontaktLista") or []
    if contacts:
        lines = []
        for c in contacts[:6]:  # avoid huge notes
            nm = c.get("Namn") or ""
            em = c.get("Epost") or ""
            rl = c.get("Roll") or ""
            tel = c.get("Telefon") or ""
            line = " / ".join([s for s in (nm, em, tel, rl) if s])
            if line:
                lines.append(line)
        if lines:
            notes = "Contacts:\n- " + "\n- ".join(lines)

    return {
        "id": f"vinnova:{uid}",
        "source": "vinnova",
        "source_uid": uid,
        "title":   {"sv": title_sv,   "en": title_en},
        "summary": {"sv": summary_sv, "en": summary_en},
        "programme": programme,
        "sponsor": "Vinnova",
        "tags": tags,
        "deadlines": deadlines,
        "status": status,
        "links": links,
        "opens_at": opens_at,
        "closes_at": closes_at,
        "notes": notes,
    }



def normalize_ftop(x: dict) -> dict:
    uid = str(x.get("id") or x.get("callIdentifier") or "")
    title = x.get("title") or {}
    title_en = title.get("en") if isinstance(title, dict) else (title or None)
    # Some fields may be nested or strings; be permissive.
    summary_en = None
    opens = (x.get("openingDate") or "")[:10] or None
    closes = (x.get("deadlineDate") or "")[:10] or None
    link = x.get("url") or None

    return {
        "id": f"euftop:{uid}",
        "source": "eu_ftop",
        "source_uid": uid,
        "title": {"en": title_en, "sv": None},
        "summary": {"en": summary_en, "sv": None},
        "programme": None,
        "sponsor": "European Commission",
        "tags": ["eu", "horizon-europe"],
        "deadlines": [{"type": "single", "date": closes}] if closes else [],
        "status": "open",  # API filter already constrained to OPEN
        "links": {"landing": link},
        "opens_at": opens,
        "closes_at": closes,
        "notes": None,
    }
