import os
from fastapi import FastAPI, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import engine, get_db
from . import models, crud
from .schemas import OpportunityIn, OpportunityOut

app = FastAPI(title="Grants Hub API (Minimal)")

# Create DB objects on startup (simple path; Alembic can be added later)
if os.getenv("TESTING") != "1":
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[startup] DB init skipped or failed: {e}")

    try:
        with engine.begin() as conn:
            # JSON path indexes to accelerate filters/search
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_status ON opportunities (status);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_sponsor ON opportunities (sponsor);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_programme ON opportunities (programme);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_closes_at ON opportunities (closes_at);
            """))
            # Title/summary English text indexes (functional)
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_title_en
                ON opportunities ((title->>'en'));
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_summary_en
                ON opportunities ((summary->>'en'));
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_title_sv
                ON opportunities ((title->>'sv'));
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_opps_summary_sv
                ON opportunities ((summary->>'sv'));
            """))
        print("[startup] Index checks complete")
    except Exception as e:
        print(f"[startup] Index creation skipped: {e}")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities", response_model=list[OpportunityOut])
def list_opps(
    response: Response,
    q: str | None = Query(None, description="Free text search"),
    status: str | None = Query(None, pattern="^(open|planned|closed)$"),
    sponsor: str | None = None,
    programme: str | None = None,
    tag: str | None = None,
    deadline_before: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    deadline_after: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    sort: str = Query("recent", pattern="^(recent|deadline_asc|deadline_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows, total = crud.search_opportunities(
        db,
        q=q, status=status, sponsor=sponsor, programme=programme, tag=tag,
        deadline_before=deadline_before, deadline_after=deadline_after,
        sort=sort, page=page, page_size=page_size,
    )
    # Pagination metadata via headers (simple, frontend-friendly)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    return rows

@app.post("/opportunities", response_model=OpportunityOut)
def create_or_update(opportunity: OpportunityIn, db: Session = Depends(get_db)):
    return crud.upsert_opportunity(db, opportunity)

# Dev-only helper to seed one record
@app.post("/_seed")
def seed(db: Session = Depends(get_db)):
    sample = OpportunityIn(
        id="demo-1",
        source="demo",
        source_uid="demo-1",
        title={"en": "Demo call for electric aviation", "sv": "Demo-utlysning för elflyg"},
        summary={"en": "Testing pipeline", "sv": "Testar pipeline"},
        programme="National",
        sponsor="Example Sponsor",
        tags=["electric aviation"],
        deadlines=[{"type":"single","date":"2025-12-01"}],
        status="open",
        links={"landing":"https://example.org"}
    )
    return {"inserted": 1} if crud.upsert_opportunity(db, sample) else {"inserted": 0}
