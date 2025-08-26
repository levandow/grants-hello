# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, cast, String
from datetime import date
from . import models
from .schemas import OpportunityIn

def _ilike(col, term: str):
    # portable case-insensitive LIKE
    return func.lower(col).like(f"%{term.lower()}%")

def _to_date(iso: str):
    # expects YYYY-MM-DD (normalizer ensures this)
    return func.to_date(iso, "YYYY-MM-DD")

def search_opportunities(
    db: Session,
    *,
    q: str | None = None,
    status: str | None = None,
    sponsor: str | None = None,
    programme: str | None = None,
    tag: str | None = None,
    deadline_before: str | None = None,
    deadline_after: str | None = None,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 20,
):
    """Search + filter + sort + paginate (PostgreSQL)."""
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    O = models.Opportunity
    stmt = select(O)
    conds = []

    if status:
        conds.append(O.status == status)
    if sponsor:
        conds.append(O.sponsor == sponsor)
    if programme:
        conds.append(O.programme == programme)
    if tag:
        # Portable: cast JSON array to text and do a LIKE match
        conds.append(_ilike(cast(O.tags, String), tag))

    if deadline_before:
        conds.append(O.closes_at.is_not(None))
        conds.append(O.closes_at <= _to_date(deadline_before))
    if deadline_after:
        conds.append(O.closes_at.is_not(None))
        conds.append(O.closes_at >= _to_date(deadline_after))

    if q:
        t_en = O.title.op("->>")("en")
        t_sv = O.title.op("->>")("sv")
        s_en = O.summary.op("->>")("en")
        s_sv = O.summary.op("->>")("sv")
        conds.append(or_(_ilike(t_en, q), _ilike(t_sv, q), _ilike(s_en, q), _ilike(s_sv, q)))

    if conds:
        stmt = stmt.where(and_(*conds))

    if sort == "deadline_asc":
        stmt = stmt.order_by(O.closes_at.asc().nulls_last())
    elif sort == "deadline_desc":
        stmt = stmt.order_by(O.closes_at.desc().nulls_last())
    else:
        # placeholder for "recent" until an updated_at field exists
        stmt = stmt.order_by(O.id.desc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset(offset).limit(page_size)).scalars().all()
    return rows, total

# ---- existing helpers (keep them) ------------------------------------------

def _coerce_date(v):
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(v)

def upsert_opportunity(db: Session, data: OpportunityIn):
    payload = data.model_dump()
    payload["opens_at"]  = _coerce_date(payload.get("opens_at"))
    payload["closes_at"] = _coerce_date(payload.get("closes_at"))

    O = models.Opportunity
    obj = db.query(O).filter(O.source_uid == data.source_uid).one_or_none()
    if obj is None:
        obj = O(**payload)
        db.add(obj)
    else:
        for k, v in payload.items():
            setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return obj

def list_opportunities(db: Session, limit: int = 50, offset: int = 0):
    O = models.Opportunity
    return (
        db.query(O)
        .order_by(O.closes_at.desc().nulls_last())
        .offset(offset)
        .limit(limit)
        .all()
    )
