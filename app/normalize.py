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

    # Topic codes array
    codes = out.get("topic_codes")
    if isinstance(codes, list):
        out["topic_codes"] = [str(c).strip() for c in codes if c]
    elif codes:
        out["topic_codes"] = [str(codes).strip()]
    else:
        out["topic_codes"] = []

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

def _status_from_dates_or_year(opens_at: Optional[str], closes_at: Optional[str], dnr: str) -> str:
    # 1) If dates exist → use them.
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
    # 2) No dates → infer from diary number year (e.g., "2014-04155").
    try:
        year = int((dnr or "")[:4])
        if year < today.year:
            return "closed"
    except Exception:
        pass
    return "open"

def _extract_link(obj: Any) -> str:
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        for k in ("URL", "Url", "url", "HRef", "href", "link", "fileURL", "FileURL"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""

def _clean_text(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s2 = s.strip()
    if not s2 or s2.lower() == "x":
        return None
    return s2

def normalize_vinnova(u: dict) -> dict:
    # IDs
    dnr = (u.get("Diarienummer") or u.get("DiarienummerUtlysning") or "").strip()
    uid = dnr or f"vno-{abs(hash((u.get('Titel') or u.get('TitelEngelska') or '').lower()))}"

    # Titles
    title_sv = _clean_text(u.get("Titel"))
    title_en = _clean_text(u.get("TitelEngelska"))
    if not title_en and title_sv:
        title_en = title_sv  # fallback to Swedish

    # Summary: prefer first WebText paragraph; fallback to Beskrivning fields
    summary_sv = None
    summary_en = None
    webtexts = u.get("WebTextLista") or []
    if isinstance(webtexts, list) and webtexts:
        w0 = webtexts[0] or {}
        summary_sv = _clean_text(w0.get("TextSv")) or _clean_text(u.get("Beskrivning"))
        summary_en = _clean_text(w0.get("TextEn")) or _clean_text(u.get("BeskrivningEngelska"))
    else:
        summary_sv = _clean_text(u.get("Beskrivning"))
        summary_en = _clean_text(u.get("BeskrivningEngelska")) or summary_sv

    # Programme: infer Innovair if in title
    programme = None
    tblob = " ".join([t for t in [title_sv or "", title_en or ""]])
    if "innovair" in tblob.lower():
        programme = "Innovair"

    # Links
    links: Dict[str, str] = {}
    # 1) LankLista → landing
    for item in (u.get("LankLista") or []):
        url = _extract_link(item)
        if url:
            links["landing"] = url
            break
    # 2) Primary document → guidelines
    for doc in (u.get("DokumentLista") or []):
        if doc.get("Primary"):
            links["guidelines"] = doc.get("fileURL") or _extract_link(doc) or ""
            break
    # 3) If still no landing, fall back to guidelines (so there is always a click target)
    if not links.get("landing"):
        links["landing"] = links.get("guidelines", "") or ""
    # Ensure string
    links["landing"] = links.get("landing", "") or ""

    # Dates
    opens_at  = _iso_or_none(u.get("Oppningsdatum") or u.get("Öppningsdatum") or u.get("OpeningDate"))
    closes_at = _iso_or_none(u.get("Stangningsdatum") or u.get("Stängningsdatum") or u.get("ClosingDate"))

    deadlines: List[Dict[str, Any]] = []
    if closes_at:
        deadlines.append({"type": "single", "date": closes_at})

    # Status (dates or diary-year fallback)
    status = _status_from_dates_or_year(opens_at, closes_at, dnr)

    # Tags
    tags = ["sweden", "public-funder"]
    text_blob = " ".join(filter(None, [title_sv, title_en, summary_sv, summary_en])).lower()
    if any(k in text_blob for k in ("flyg", "aero", "air", "aviation")):
        tags.append("aviation")
    if any(k in text_blob for k in ("smf", "sme")):
        tags.append("sme")

    # Contacts → notes (dev-friendly; schema has no contacts field)
    notes = None
    contacts = u.get("KontaktLista") or []
    if contacts:
        lines = []
        for c in contacts[:6]:
            nm = (c.get("Namn") or "").strip()
            em = (c.get("Epost") or "").strip()
            tel = (c.get("Telefon") or "").strip()
            rl = (c.get("Roll") or "").strip()
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
        "topic_codes": [],
        "tags": tags,
        "deadlines": deadlines,
        "status": status,
        "links": links,
        "opens_at": opens_at,
        "closes_at": closes_at,
        "notes": notes,
    }

def normalize_vinnova_round(r: dict) -> dict:
    """
    Normalize an Ansökningsomgång (application round) record into the unified schema.
    Fields in the feed often include:
      - AnsokningsomgangDnr or Diarienummer  (unique id for the round)
      - Titel / TitelEngelska
      - Oppningsdatum / Stangningsdatum (open/close)
      - LankLista (list of links; objects with URL/Beskrivning)
      - DokumentLista (files; fileURL or DokumentID)
      - WebTextLista (TextSv/TextEn paragraphs)
      - Sponsor/program info may be implicit (Vinnova / programme name in title)
    """
    def _get(*names):
        for n in names:
            if n in r and r[n] not in (None, ""):
                return r[n]
        return None

    def _extract_link(obj):
        if isinstance(obj, str):
            return obj.strip()
        if isinstance(obj, dict):
            for k in ("URL","Url","url","HRef","href","link"):
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        return ""

    def _doc_url(d: dict) -> str:
        url = (d.get("fileURL") or d.get("URL") or "").strip() if isinstance(d, dict) else ""
        if url:
            return url
        did = (d.get("DokumentID") or "").strip() if isinstance(d, dict) else ""
        return f"https://data.vinnova.se/api/file/{did}" if did else ""

    # IDs
    dnr = (_get("AnsokningsomgangDnr", "Diarienummer", "Dnr") or "").strip()
    uid = dnr or f"vno-round-{abs(hash((_get('Titel','TitelEngelska') or '').lower()))}"

    # Titles
    title_sv = (_get("Titel") or "").strip() or None
    title_en = (_get("TitelEngelska") or "").strip() or None

    # Summary (prefer first web paragraph)
    summary_sv = None; summary_en = None
    w = r.get("WebTextLista") or []
    if isinstance(w, list) and w:
        summary_sv = (w[0].get("TextSv") or "").strip() or None
        summary_en = (w[0].get("TextEn") or "").strip() or None
    if not summary_sv:
        summary_sv = (_get("Beskrivning", "Sammanfattning") or "").strip() or None
    if not summary_en:
        summary_en = (_get("BeskrivningEngelska", "SummaryEnglish") or "").strip() or None

    # Programme (heuristic from title)
    programme = "Innovair" if (title_sv or title_en or "").lower().__contains__("innovair") else None

    # Links
    links = {}
    # landing: first link in LankLista if present
    for item in (r.get("LankLista") or []):
        url = _extract_link(item)
        if url:
            links["landing"] = url
            break
    # guidelines: primary document
    primary = None
    for d in (r.get("DokumentLista") or []):
        if isinstance(d, dict) and d.get("Primary"):
            primary = d; break
    if primary:
        links["guidelines"] = _doc_url(primary)
    # if no landing at all, fall back to any doc
    if not links.get("landing"):
        for d in (r.get("DokumentLista") or []):
            url = _doc_url(d)
            if url:
                links["landing"] = url
                links.setdefault("guidelines", url)
                break
    links["landing"] = links.get("landing", "") or ""

    # Dates
    opens_at  = _iso_or_none(_get("Oppningsdatum", "Öppningsdatum", "OpeningDate"))
    closes_at = _iso_or_none(_get("Stangningsdatum", "Stängningsdatum", "ClosingDate"))

    deadlines = []
    if closes_at:
        deadlines.append({"type": "single", "date": closes_at})

    # Status
    status = _status_from_dates_or_year(opens_at, closes_at, dnr or "")

    # Tags (light)
    tags = ["sweden", "public-funder"]
    text_blob = " ".join(filter(None, [title_sv, title_en, summary_sv, summary_en])).lower()
    if any(k in text_blob for k in ("flyg", "aero", "air", "aviation")): tags.append("aviation")
    if any(k in text_blob for k in ("smf", "sme")): tags.append("sme")

    # Notes (optional: contacts etc., if present on rounds)
    notes = None
    contacts = r.get("KontaktLista") or []
    if contacts:
        lines = []
        for c in contacts[:6]:
            nm = (c.get("Namn") or "").strip()
            em = (c.get("Epost") or "").strip()
            tel = (c.get("Telefon") or "").strip()
            rl = (c.get("Roll") or "").strip()
            line = " / ".join([s for s in (nm, em, tel, rl) if s])
            if line: lines.append(line)
        if lines: notes = "Contacts:\n- " + "\n- ".join(lines)

    return {
        "id": f"vinnova_round:{uid}",
        "source": "vinnova_rounds",
        "source_uid": uid,
        "title":   {"sv": title_sv,   "en": title_en},
        "summary": {"sv": summary_sv, "en": summary_en},
        "programme": programme,
        "sponsor": "Vinnova",
        "topic_codes": [],
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

    def _pick_text(obj: Any, lang: str = "en") -> str | None:
        """Return first non-empty text from nested structures."""
        if not obj:
            return None
        if isinstance(obj, str):
            s = obj.strip()
            return s or None
        if isinstance(obj, list):
            for item in obj:
                v = _pick_text(item, lang)
                if v:
                    return v
            return None
        if isinstance(obj, dict):
            if lang in obj and obj[lang]:
                return _pick_text(obj[lang], lang)
            for key in ("value", "text", "label", "title", "default", "defaultValue"):
                v = obj.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            for v in obj.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, (dict, list)):
                    vv = _pick_text(v, lang)
                    if vv:
                        return vv
        return None

    def _pick_date(v: Any) -> str | None:
        if isinstance(v, dict):
            for key in ("date", "value", "startDate", "endDate"):
                if v.get(key):
                    return _iso_or_none(v.get(key))
        return _iso_or_none(v)

    title_en = _pick_text(x.get("title"))
    summary_en = _pick_text(
        x.get("summary")
        or x.get("objective")
        or x.get("objectiveText")
        or x.get("description")
    )

    programme = _pick_text(x.get("programme") or x.get("program"))

    opens = _pick_date(x.get("openingDate"))
    closes = _pick_date(x.get("deadlineDate"))

    deadlines: List[Dict[str, Any]] = []
    for d in x.get("deadlineDates") or x.get("deadlines") or []:
        dt = _pick_date(d.get("date") if isinstance(d, dict) else d)
        if dt:
            deadlines.append({"type": "single", "date": dt})
    if not deadlines and closes:
        deadlines.append({"type": "single", "date": closes})

    status_raw = x.get("status")
    if isinstance(status_raw, dict):
        status_raw = (
            status_raw.get("id")
            or status_raw.get("code")
            or status_raw.get("value")
            or status_raw.get("label")
        )
    status_map = {
        "31094502": "open",
        "31094505": "closed",
        "31094501": "planned",
        "open": "open",
        "closed": "closed",
        "planned": "planned",
    }
    status = status_map.get(str(status_raw).strip().lower(), "open")

    link = ""
    for key in ("url", "topicUrl", "topicURL", "link", "links"):
        v = x.get(key)
        if not v:
            continue
        if isinstance(v, list):
            for item in v:
                link = _extract_link(item)
                if link:
                    break
        else:
            link = _extract_link(v)
        if link:
            break

    topic_codes: List[str] = []
    for key in ("topic", "topics", "topicId", "topicIdentifier"):
        v = x.get(key)
        if not v:
            continue
        if isinstance(v, list):
            topic_codes.extend(str(t) for t in v if t)
        else:
            topic_codes.append(str(v))
    cid = x.get("callIdentifier")
    if cid:
        topic_codes.append(str(cid))
    # deduplicate
    seen: set[str] = set()
    topic_codes = [t for t in topic_codes if not (t in seen or seen.add(t))]

    return {
        "id": f"euftop:{uid}",
        "source": "eu_ftop",
        "source_uid": uid,
        "title": {"en": title_en, "sv": None},
        "summary": {"en": summary_en, "sv": None},
        "programme": programme,
        "sponsor": "European Commission",
        "topic_codes": topic_codes,
        "tags": ["eu", "horizon-europe"],
        "deadlines": deadlines,
        "status": status,
        "links": {"landing": link},
        "opens_at": opens,
        "closes_at": closes,
        "notes": None,
    }
