from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from . import models
from datetime import date

def _ilike(col, term: str):
    return func.lower(col).ilike(f"%{term.lower()}%")

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
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    O = models.Opportunity
    query = select(O)

    # Filters
    conds = []
    if status:
        conds.append(O.status == status)
    if sponsor:
        conds.append(O.sponsor == sponsor)
    if programme:
        conds.append(O.programme == programme)
    if tag:
        # tags stored as JSON array; use PostgreSQL ? operator via contains
        conds.append(func.jsonb_contains(O.tags, func.to_jsonb([tag])) | func.jsonb_contains(O.tags, func.to_jsonb(tag)))
        # fallback for simple array containment if jsonb_contains not available:
        # conds.append(func.cast(O.tags, JSONB).contains([tag]))

    if deadline_before:
        conds.append(O.closes_at != None)
        conds.append(O.closes_at <= func.to_date(deadline_before, 'YYYY-MM-DD'))
    if deadline_after:
        conds.append(O.closes_at != None)
        conds.append(O.closes_at >= func.to_date(deadline_after, 'YYYY-MM-DD'))

    if q:
        # Search across title/summary in sv/en
        t_en = (O.title.op("->>")("en"))
        t_sv = (O.title.op("->>")("sv"))
        s_en = (O.summary.op("->>")("en"))
        s_sv = (O.summary.op("->>")("sv"))
        search_cond = or_(
            _ilike(t_en, q),
            _ilike(t_sv, q),
            _ilike(s_en, q),
            _ilike(s_sv, q),
        )
        conds.append(search_cond)

    if conds:
        query = query.where(and_(*conds))

    # Sorting
    if sort == "deadline_asc":
        query = query.order_by(O.closes_at.asc().nulls_last())
    elif sort == "deadline_desc":
        query = query.order_by(O.closes_at.desc().nulls_last())
    else:  # "recent"
        query = query.order_by(O.id.desc())  # simple proxy; replace with updated_at when added

    # Count for pagination
    count_q = select(func.count()).select_from(query.subquery())
    total = db.execute(count_q).scalar_one()

    rows = db.execute(query.offset(offset).limit(page_size)).scalars().all()
    return rows, total
