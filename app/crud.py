from __future__ import annotations

from datetime import date
from typing import Optional, Tuple, List

from sqlalchemy import select, func, and_, or_, cast, String, text
from sqlalchemy.orm import Session

from . import models
from .schemas import OpportunityIn


# --------------------------- helpers ---------------------------

def _coerce_date(v) -> Optional[date]:
    """Accept ISO 'YYYY-MM-DD' or None; return datetime.date or None."""
    if v in (None, "", "null"):
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None

def _ilike(col, term: str):
    """Portable case-insensitive LIKE."""
    # Using lower() LIKE for portability (instead of ILIKE which is PG-only in some dialects)
    return func.lower(col).like(f"%{term.lower()}%")


# --------------------------- write path ---------------------------

def upsert_opportunity(db: Session, data: OpportunityIn) -> models.Opportunity:
    """
    Idempotent upsert keyed on source_uid.
    Coerces date strings to date objects for Date columns.
    """
    payload = data.model_dump()

    # Ensure date types for the DB Date columns
    payload["opens_at"] = _coerce_date(payload.get("opens_at"))
    payload["closes_at"] = _coerce_date(payload.get("closes_at"))

    # Separate unknown keys into the "extra" JSON column
    cols = set(c.name for c in models.Opportunity.__table__.columns)
    extras = {k: payload.pop(k) for k in list(payload.keys()) if k not in cols}

    O = models.Opportunity
    obj = db.query(O).filter(O.source_uid == data.source_uid).one_or_none()

    if obj is None:
        payload["extra"] = extras
        obj = O(**payload)
        db.add(obj)
    else:
        # Merge new extras with existing ones
        merged_extra = dict(getattr(obj, "extra", {}) or {})
        merged_extra.update(extras)
        payload["extra"] = merged_extra
        for k, v in payload.items():
            setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return obj


# --------------------------- read/search path ---------------------------

def search_opportunities(
    db: Session,
    *,
    q: Optional[str] = None,
    status: Optional[str] = None,
    sponsor: Optional[str] = None,
    programme: Optional[str] = None,
    tag: Optional[str] = None,
    deadline_before: Optional[str] = None,
    deadline_after: Optional[str] = None,
    sort: str = "recent",         # recent | deadline_asc | deadline_desc
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[models.Opportunity], int]:
    """
    Full-featured search with filters + sorting + pagination.
    - Text search over title/summary in sv/en (JSON->>key)
    - Filters: status, sponsor, programme, tag, deadline range
    - Sorting: recent (by id desc), deadline_asc, deadline_desc
    - Pagination: page/page_size
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    O = models.Opportunity
    stmt = select(O)
    conds = []

    # Filters
    if status:
        conds.append(O.status == status)
    if sponsor:
        conds.append(O.sponsor == sponsor)
    if programme:
        conds.append(O.programme == programme)
    if tag:
        from sqlalchemy import text
        # Portable: LOWER(CAST(tags AS TEXT)) LIKE '%tag%'
        conds.append(func.lower(cast(O.tags, String)).like(f"%{tag.lower()}%"))

    # Deadline window (strings → Python dates, compare with Date column)
    d_after = _coerce_date(deadline_after)
    d_before = _coerce_date(deadline_before)
    if d_after:
        conds.append(O.closes_at.isnot(None))
        conds.append(O.closes_at >= d_after)
    if d_before:
        conds.append(O.closes_at.isnot(None))
        conds.append(O.closes_at <= d_before)

    # Free-text search across localized title/summary (Postgres JSON ->> operator)
    if q:
        t_en = O.title.op("->>")("en")
        t_sv = O.title.op("->>")("sv")
        s_en = O.summary.op("->>")("en")
        s_sv = O.summary.op("->>")("sv")
        conds.append(or_(_ilike(t_en, q), _ilike(t_sv, q), _ilike(s_en, q), _ilike(s_sv, q)))

    if conds:
        stmt = stmt.where(and_(*conds))

    # Sorting
    if sort == "deadline_asc":
        stmt = stmt.order_by(O.closes_at.asc().nulls_last())
    elif sort == "deadline_desc":
        stmt = stmt.order_by(O.closes_at.desc().nulls_last())
    else:
        # "recent" proxy until an updated_at field exists
        stmt = stmt.order_by(O.id.desc())

    # Count + page
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()
    return rows, total


def list_opportunities(db: Session, limit: int = 50, offset: int = 0) -> List[models.Opportunity]:
    """Simple listing (older fallback)."""
    O = models.Opportunity
    return (
        db.query(O)
        .order_by(O.closes_at.desc().nulls_last())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_facets(db: Session) -> dict:
    """Collect distinct values used for filtering (facets)."""
    O = models.Opportunity

    sponsors = [
        r[0]
        for r in db.query(O.sponsor)
        .filter(O.sponsor.isnot(None))
        .distinct()
        .order_by(O.sponsor)
    ]

    programmes = [
        r[0]
        for r in db.query(O.programme)
        .filter(O.programme.isnot(None))
        .distinct()
        .order_by(O.programme)
    ]

    statuses = [r[0] for r in db.query(O.status).distinct().order_by(O.status)]

    tag_rows = db.query(O.tags).all()
    tag_set = set()
    for arr, in tag_rows:
        if arr:
            tag_set.update(arr)
    tags = sorted(tag_set)

    return {
        "sponsors": sponsors,
        "programmes": programmes,
        "statuses": statuses,
        "tags": tags,
    }
