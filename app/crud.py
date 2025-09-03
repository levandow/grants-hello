# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, cast, String
from datetime import date
from . import models
from .schemas import OpportunityIn
from typing import Optional, List

def _ilike(col, term: str):
    # portable case-insensitive LIKE
    return func.lower(col).like(f"%{term.lower()}%")

def _to_date(iso: str):
    # expects YYYY-MM-DD (normalizer ensures this)
    return func.to_date(iso, "YYYY-MM-DD")

def search_opportunities(
    db: Session = SessionLocal(),
    sponsor: Optional[str] = None,
    query: Optional[str] = None,
    tags: Optional[str] = None,
    status: Optional[str] = None,
    deadline_after: Optional[date] = None,
    deadline_before: Optional[date] = None,
    sort: Optional[str] = "deadline_desc",
    page: int = 1,
    page_size: int = 10,
):
    q = db.query(Opportunity)

    if sponsor:
        q = q.filter(Opportunity.sponsor.ilike(f"%{sponsor}%"))

    if query:
        q = q.filter(
            or_(
                Opportunity.title["sv"].astext.ilike(f"%{query}%"),
                Opportunity.title["en"].astext.ilike(f"%{query}%"),
                Opportunity.summary["sv"].astext.ilike(f"%{query}%"),
                Opportunity.summary["en"].astext.ilike(f"%{query}%"),
            )
        )

    if tags:
        for tag in tags.split(","):
            q = q.filter(Opportunity.tags.contains([tag.strip()]))

    if status:
        q = q.filter(Opportunity.status == status)

    if deadline_after:
        q = q.filter(Opportunity.closes_at != None, Opportunity.closes_at >= deadline_after)

    if deadline_before:
        q = q.filter(Opportunity.closes_at != None, Opportunity.closes_at <= deadline_before)

    total = q.count()

    if sort == "deadline_asc":
        q = q.order_by(Opportunity.closes_at.asc().nullslast())
    elif sort == "deadline_desc":
        q = q.order_by(Opportunity.closes_at.desc().nullslast())

    results = q.offset((page - 1) * page_size).limit(page_size).all()
    return results, total

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
