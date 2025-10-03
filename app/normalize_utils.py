# normalize_utils.py
import re
from html.parser import HTMLParser
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# --- Simple HTML tools (stdlib only) ---

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

def extract_links(html: Optional[str]) -> List[Dict[str, str]]:
    if not html:
        return []
    p = _LinkExtractor()
    try:
        p.feed(html)
    except Exception:
        return []
    # normalize + de-dupe
    seen = set()
    out = []
    for href, text in p.links:
        href = (href or "").strip()
        text = (text or "").strip()
        if not href:
            continue
        key = (href, text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": href, "label": text or None})
    return out

def strip_html(html: Optional[str]) -> Optional[str]:
    if not html:
        return None
    # remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip() or None

# --- Dates & status ---

# EU sometimes uses "19 January 2025", plus ISO strings; Vinnova uses ISO.
_DATE_FMTS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
    "%d %B %Y",          # 19 January 2025
    "%d %b %Y",          # 19 Jan 2025
)

def parse_date_maybe(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    # normalize timezone suffix like +0000 → +00:00 (drop for date)
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
    # if looks like ISO with time, keep date part quickly
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    # last resort: yyyy-mm-dd somewhere in string
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", s)
    return m.group(1) if m else None

def compute_deadline_date(deadlines: List[Dict[str, Optional[str]]]) -> Optional[str]:
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

def compute_status(opening_date: Optional[str], deadline_date: Optional[str]) -> str:
    if not opening_date and not deadline_date:
        return "unknown"
    today = datetime.now(timezone.utc).date()
    if opening_date:
        try:
            od = datetime.strptime(opening_date, "%Y-%m-%d").date()
        except ValueError:
            od = None
    else:
        od = None
    if deadline_date:
        try:
            dd = datetime.strptime(deadline_date, "%Y-%m-%d").date()
        except ValueError:
            dd = None
    else:
        dd = None

    if od and today < od:
        return "upcoming"
    if dd and today <= dd:
        return "open"
    if dd and today > dd:
        return "closed"
    return "unknown"

# --- Documents vs links ---

_DOC_KEYWORDS = (
    "call", "work programme", "work program", "guide", "guidance",
    "template", "terms", "conditions", "instructions"
)

def split_documents_vs_links(links: List[Dict[str, Optional[str]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Heuristic: PDFs or labels suggesting formal documents → documents; others → links."""
    docs, other = [], []
    for l in links:
        url = (l.get("url") or "").strip()
        label = (l.get("label") or "").strip()
        lower = f"{label} {url}".lower()
        is_pdf = url.lower().endswith(".pdf")
        is_doc_like = is_pdf or any(k in lower for k in _DOC_KEYWORDS)
        item = {"title": label or None, "description": None, "url": url, "lang": None,
                "primary": None, "filename": None, "external_id": None}
        if is_doc_like:
            docs.append(item)
        else:
            other.append({"label": label or None, "url": url})
    # de-duplicate by URL
    def dedupe(lst, key):
        seen = set(); out=[]
        for x in lst:
            k = x.get(key)
            if k and k not in seen:
                seen.add(k); out.append(x)
        return out
    return dedupe(docs, "url"), dedupe(other, "url")
