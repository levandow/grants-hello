# app/normalize.py
import json
import re
from html.parser import HTMLParser
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Shared helpers (stdlib)
# =========================

def _ensure_str(x: Optional[str]) -> str:
    return x if isinstance(x, str) else ""

class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[Tuple[str, str]] = []
        self._in_a = False
        self._href = ""
        self._text_chunks: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._in_a = True
            self._href = dict(attrs).get("href", "")

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._in_a:
            text = " ".join(self._text_chunks).strip()
            self.links.append((self._href, text))
            self._in_a = False
            self._href = ""
            self._text_chunks = []

    def handle_data(self, data):
        if self._in_a:
            self._text_chunks.append(data)

def _extract_links(html: Optional[str]) -> List[Dict[str, Optional[str]]]:
    if not html:
        return []
    p = _LinkExtractor()
    try:
        p.feed(html)
    except Exception:
        return []
    seen = set()
    out: List[Dict[str, Optional[str]]] = []
    for href, text in p.links:
        href = (href or "").strip()
        text = (text or "").strip() or None
        if not href:
            continue
        key = (href, text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": href, "label": text})
    return out

def _strip_html(html: Optional[str]) -> Optional[str]:
    if not html:
        return None
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip() or None

def _truncate(s: Optional[str], max_len: int) -> Optional[str]:
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= max_len else s[: max_len - 1] + "…"

_DATE_FMTS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%d %B %Y",      # 19 January 2025
    "%d %b %Y",      # 19 Jan 2025
)

def _parse_date_maybe(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)  # +0000 -> +00:00
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", s)
    return m.group(1) if m else None

def _compute_deadline_date(deadlines: List[Dict[str, Optional[str]]]) -> Optional[str]:
    """Pick the next upcoming date; if none upcoming, return the latest past (for display)."""
    today = datetime.now(timezone.utc).date()
    parsed = []
    for d in deadlines:
        ds = d.get("date")
        if not ds:
            continue
        try:
            parsed.append(datetime.strptime(ds, "%Y-%m-%d").date())
        except ValueError:
            pass
    if not parsed:
        return None
    future = sorted([d for d in parsed if d >= today])
    if future:
        return future[0].isoformat()
    return max(parsed).isoformat()

def _compute_status(opening_date: Optional[str], deadline_date: Optional[str]) -> str:
    if not opening_date and not deadline_date:
        return "Unknown"
    today = datetime.now(timezone.utc).date()
    od = None
    dd = None
    if opening_date:
        try:
            od = datetime.strptime(opening_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    if deadline_date:
        try:
            dd = datetime.strptime(deadline_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    if od and today < od:
        return "Forthcoming"
    if dd and today <= dd:
        return "Open"
    if dd and today > dd:
        return "Closed"
    return "Unknown"

_DOC_KEYWORDS = (
    "call", "work programme", "work program", "guide", "guidance",
    "template", "terms", "conditions", "instructions"
)

def _split_documents_vs_links(links: List[Dict[str, Optional[str]]]):
    """PDFs or doc-like labels -> documents; others -> links."""
    docs, other = [], []
    for l in links:
        url = (l.get("url") or "").strip()
        label = (l.get("label") or "").strip()
        lower = f"{label} {url}".lower()
        is_pdf = url.lower().endswith(".pdf")
        is_doc_like = is_pdf or any(k in lower for k in _DOC_KEYWORDS)
        doc_item = {
            "title": label or None, "description": None, "url": url, "lang": None,
            "primary": None, "filename": None, "external_id": None
        }
        if is_doc_like:
            docs.append(doc_item)
        else:
            other.append({"label": label or None, "url": url})
    # de-dup by URL
    def dedupe(lst, key):
        seen = set(); out = []
        for x in lst:
            k = x.get(key)
            if k and k not in seen:
                seen.add(k); out.append(x)
        return out
    return dedupe(docs, "url"), dedupe(other, "url")

def _first(x):
    return x[0] if isinstance(x, list) and x else None

# =========================
# VINNOVA normalizer
# =========================

def normalize_vinnova(rec: Dict[str, Any]) -> Dict[str, Any]:
    # Titles & descriptions (prefer English, fallback Swedish)
    title_sv = rec.get("Titel")
    title_en = rec.get("TitelEngelska")
    desc_html = rec.get("BeskrivningEngelska") or rec.get("Beskrivning")
    desc_text = _strip_html(desc_html)

    # Multilingual title/summary dicts
    title_dict = {"sv": title_sv, "en": title_en}

    summary_sv = None
    summary_en = None
    for w in (rec.get("WebTextLista") or []):
        if not summary_en and w.get("TextEn"):
            summary_en = w["TextEn"]
        if not summary_sv and w.get("TextSv"):
            summary_sv = w["TextSv"]
    if not summary_sv and desc_text:
        summary_sv = desc_text[:400]
    if not summary_en and desc_text:
        summary_en = desc_text[:400]
    summary_dict = {"sv": summary_sv, "en": summary_en}

    # Dates
    opening_date = _parse_date_maybe(rec.get("Oppningsdatum"))
    closing = _parse_date_maybe(rec.get("Stangningsdatum"))
    deadlines = [{"type": "single", "date": d} for d in [closing] if d]  # API requires 'type'

    # Documents (already structured)
    documents = []
    for d in (rec.get("DokumentLista") or []):
        documents.append({
            "title": d.get("Titel"),
            "description": d.get("Beskrivning"),
            "url": d.get("fileURL"),
            "lang": d.get("Lang"),
            "primary": bool(d.get("Primary")) if d.get("Primary") is not None else None,
            "filename": d.get("FileName"),
            "external_id": d.get("DokumentID"),
        })

    # Links (structured) → plus classify doc-like links into documents
    links_list = []
    for l in (rec.get("LankLista") or []):
        links_list.append({"label": l.get("Beskrivning") or None, "url": l.get("URL") or ""})
    doclike_from_links, links_list = _split_documents_vs_links(links_list)
    documents = doclike_from_links + documents

    # Apply URL heuristic
    apply_url = None
    for l in links_list:
        if (l.get("label") or "").lower().find("Ansök här") >= 0:
            apply_url = l.get("url"); break

    # Links object required by API (strings, not null)
    diarienummer = rec.get("Diarienummer")
    if diarienummer:
        landing = f"https://www.vinnova.se/ao/{diarienummer}"
    else:
        landing = links_list[0]["url"] if links_list else (rec.get("Webbsida") or apply_url)
    landing = _ensure_str(landing)
    apply_url = _ensure_str(apply_url or landing)
    links_obj = {"landing": landing, "apply": apply_url}

    # Contacts
    contacts = []
    for c in (rec.get("KontaktLista") or []):
        contacts.append({
            "name": c.get("Namn"),
            "email": c.get("Epost"),
            "phone": c.get("Telefon"),
            "role": c.get("Roll"),
            "external_id": c.get("KontaktID"),
        })

    language = ["en"] if (title_en or rec.get("BeskrivningEngelska")) else ["sv"]

    # Required IDs
    source_uid = rec.get("Diarienummer") or (rec.get("DiarienummerUtlysning") or _ensure_str(title_en or title_sv) or "unknown")
    deadline_date = _compute_deadline_date(deadlines) if deadlines else None
    status = _compute_status(opening_date, deadline_date)

    return {
        "id": f"VINNOVA:{source_uid}",
        "source_uid": source_uid,
        "source": "VINNOVA",
        "source_id": source_uid,  # optional duplicate; harmless
        "call_identifier": rec.get("DiarienummerUtlysning"),
        "title": title_dict,                      # dict per API
        "summary": summary_dict,                  # dict per API
        "description_html": desc_html,
        "description_text": desc_text,
        "language": language,
        "programme": None,
        "opening_date": opening_date,
        "deadline_date": deadline_date,
        "deadlines": deadlines,                   # with 'type'
        "status": status,
        "country": "SE",
        "apply_url": apply_url,
        "documents": documents,
        "contacts": contacts,
        "links": links_obj,                       # dict of strings
        "budget_total": None,
        "currency": None,
        "extra_json": rec,
    }

# =========================
# SE Generic normalizer (Formas, Forte, VR)
# =========================

def normalize_se_generic(rec: Dict[str, Any]) -> Dict[str, Any]:
    source = rec.get("finansiarNamn") or "SE_GENERIC"
    diarienummer = rec.get("diarienummer")
    source_uid = diarienummer or "unknown"

    title_sv = rec.get("titel")
    title_en = rec.get("titelEng")
    desc_sv = rec.get("beskrivning")
    desc_en = rec.get("beskrivningEng")

    title_dict = {"sv": title_sv, "en": title_en}
    summary_dict = {"sv": desc_sv, "en": desc_en}
    
    # Prefer English for generic text
    desc_text = desc_en or desc_sv

    opening_date = rec.get("oppningsdatum")
    closing_date = rec.get("stangningsdatum")
    
    deadlines = []
    if closing_date:
        deadlines.append({"type": "single", "date": closing_date})

    # Status
    raw_status = (rec.get("status") or "").lower()
    status = "Unknown"
    if "Kommande" in raw_status:
        status = "Forthcoming"
    elif "Pågående" in raw_status or "Pagaende" in raw_status:
        status = "Open"
    elif "Avslutad" in raw_status:
        status = "Closed"
    
    if status == "Unknown":
        status = _compute_status(opening_date, closing_date)

    # Links
    landing_url = ""
    pub_places = rec.get("publiceringsplatser")
    if isinstance(pub_places, list) and pub_places:
        landing_url = pub_places[0].get("webbadress") or ""
    
    links_obj = {"landing": landing_url, "apply": landing_url}

    language = ["sv"]
    if title_en or desc_en:
        language.append("en")

    return {
        "id": f"{source}:{source_uid}",
        "source_uid": source_uid,
        "source": source,
        "source_id": source_uid,
        "call_identifier": diarienummer,
        "title": title_dict,
        "summary": summary_dict,
        "description_html": None,
        "description_text": desc_text,
        "language": language,
        "programme": rec.get("program"),
        "opening_date": opening_date,
        "deadline_date": closing_date,
        "deadlines": deadlines,
        "status": status,
        "country": "SE",
        "apply_url": landing_url,
        "documents": [],
        "contacts": [],
        "links": links_obj,
        "budget_total": rec.get("budgetBelopp"),
        "currency": rec.get("budgetValuta"),
        "extra_json": rec,
        "keywords": [],
    }

# =========================
# EU normalizer
# =========================

def normalize_eu(result: Dict[str, Any]) -> Dict[str, Any]:
    meta = result.get("metadata") or {}

    # Title & descriptions
    title = _first(meta.get("title")) or result.get("summary") or _first(result.get("title"))
    desc_html = _first(meta.get("descriptionByte")) or _first(meta.get("destinationDetails")) or None
    desc_text = _strip_html(desc_html)
    summary = result.get("summary") or (desc_text[:400] if desc_text else None)

    # Multilingual dicts (EU content typically English)
    title_dict = {"en": title}
    summary_dict = {"en": summary}

    # Dates from actions (stringified JSON) + fallbacks
    opening_date = None
    raw_deadlines: List[str] = []
    status = "unknown"

    actions_raw = _first(meta.get("actions"))
    if actions_raw:
        try:
            actions = json.loads(actions_raw)
            if isinstance(actions, list) and actions:
                a0 = actions[0]
                opening_date = _parse_date_maybe(a0.get("plannedOpeningDate"))
                for d in (a0.get("deadlineDates") or []):
                    pd = _parse_date_maybe(d)
                    if pd:
                        raw_deadlines.append(pd)
                
                # Map status ID to "Forthcoming", "Open", "Closed"
                st_id = str((a0.get("status") or {}).get("id", ""))
                if st_id == "31094501":
                    status = "Forthcoming"
                elif st_id == "31094502":
                    status = "Open"
                elif st_id == "31094503":
                    status = "Closed"
                else:
                    st_abbr = (a0.get("status") or {}).get("abbreviation")
                    if isinstance(st_abbr, str) and st_abbr:
                        status = st_abbr.capitalize()
        except Exception:
            pass

    if not opening_date:
        opening_date = _parse_date_maybe(_first(meta.get("startDate")))
    if not raw_deadlines:
        dl = _parse_date_maybe(_first(meta.get("deadlineDate")))
        if dl:
            raw_deadlines.append(dl)

    deadlines = [{"type": "single", "date": d} for d in raw_deadlines]  # API requires 'type'
    deadline_date = _compute_deadline_date(deadlines) if deadlines else None
    
    if status == "unknown":
        # Try top-level status list if deep check failed
        top_status = meta.get("status") or []
        if "31094501" in top_status:
            status = "Forthcoming"
        elif "31094502" in top_status:
            status = "Open"
        elif "31094503" in top_status:
            status = "Closed"

    if status == "unknown":
        status = _compute_status(opening_date, deadline_date)

    # Sanity check: If the calculated deadline is in the past, the call is Closed,
    # regardless of what the API status says (indexes can be stale).
    if deadline_date:
        try:
            dd_obj = datetime.strptime(deadline_date, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            if dd_obj < today:
                status = "Closed"
        except ValueError:
            pass

    # Collect links: root urls + links from HTML blobs
    links_list: List[Dict[str, Optional[str]]] = []
    for u in (result.get("url") or []):
        links_list.append({"label": None, "url": u})
    for html_key in ("descriptionByte", "destinationDetails", "topicConditions", "supportInfo"):
        for html_str in (meta.get(html_key) or []):
            links_list.extend(_extract_links(html_str))

    documents, links_list = _split_documents_vs_links(links_list)

    # Landing/apply links (must be strings)
    landing = _first(meta.get("esST_URL")) or (links_list[0]["url"] if links_list else _first(result.get("url")))
    landing = _ensure_str(landing)
    apply_url = _ensure_str(landing)  # portal is the entry point; can refine later
    links_obj = {"landing": landing, "apply": apply_url}

    # Programme & identifiers
    programme_full = _first(meta.get("callTitle"))
    programme = _truncate(programme_full, 200)
    call_identifier = _first(meta.get("callIdentifier"))
    source_uid = _first(meta.get("identifier")) or result.get("reference") or _ensure_str(title) or "unknown"

    # Keywords/tags kept for enrichment (harmless if API ignores)
    keywords = (meta.get("keywords") or []) + (meta.get("tags") or [])

    return {
        "id": f"EU:{source_uid}",
        "source_uid": source_uid,
        "source": "EU",
        "source_id": source_uid,          # optional duplicate
        "call_identifier": call_identifier,
        "title": title_dict,              # dict per API
        "summary": summary_dict,          # dict per API
        "description_html": desc_html,
        "description_text": desc_text,
        "language": meta.get("language") or ([result.get("language")] if result.get("language") else ["en"]),
        "programme": programme,
        "opening_date": opening_date,
        "deadline_date": deadline_date,
        "deadlines": deadlines,           # with 'type'
        "status": status,
        "country": None,
        "apply_url": apply_url,
        "documents": documents,
        "contacts": [],                   # parse mailto: later if needed
        "links": links_obj,               # dict of strings
        "budget_total": None,
        "currency": None,
        "extra_json": result,
        "keywords": keywords,
    }

# =========================
# Unified dispatcher
# =========================

def normalize(record: Dict[str, Any], source: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize one record from either VINNOVA or EU.

    - If the record already matches the API (has 'id', 'source_uid', and 'links' is a dict),
      it's returned as-is (pass-through).
    - Pass source="VINNOVA" or source="EU" for explicit routing; otherwise we auto-detect.
    """
    # Pass-through for already-normalized payloads
    if (
        isinstance(record, dict)
        and "id" in record
        and "source_uid" in record
        and isinstance(record.get("links"), dict)
    ):
        return record

    src = (source or "").upper()
    if src == "VINNOVA":
        return normalize_vinnova(record)
    if src == "EU":
        return normalize_eu(record)
    if src in ("FORMAS", "FORTE", "VR", "VETENSKAPSRÅDET"):
        return normalize_se_generic(record)

    # Auto-detect based on shape
    if "finansiarNamn" in record:
        return normalize_se_generic(record)
    if any(k in record for k in ("Diarienummer", "Titel", "Beskrivning", "LankLista", "DokumentLista")):
        return normalize_vinnova(record)
    if isinstance(record.get("metadata"), dict):
        return normalize_eu(record)

    # Fallback: try EU then Vinnova
    try:
        return normalize_eu(record)
    except Exception:
        return normalize_vinnova(record)
