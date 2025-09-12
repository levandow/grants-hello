import os
from fastapi import FastAPI, Depends, Query, Response, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import engine, get_db
from . import models, crud
from .schemas import OpportunityIn, OpportunityOut, Facets
from typing import Optional, List
from datetime import date

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


@app.get("/facets", response_model=Facets)
def facets(db: Session = Depends(get_db)):
    return crud.get_facets(db)

@app.get("/opportunities", response_model=list[OpportunityOut])
def list_opps(
    sponsor: Optional[str] = None,
    q: Optional[str] = None,
    tags: Optional[str] = None,
    status: Optional[str] = None,
    deadline_after: Optional[date] = None,
    deadline_before: Optional[date] = None,
    sort: Optional[str] = "deadline_desc",
    page: int = 1,
    page_size: int = 10,
):
    return crud.search_opportunities(
        sponsor=sponsor,
        query=q,
        tags=tags,
        status=status,
        deadline_after=deadline_after,
        deadline_before=deadline_before,
        sort=sort,
        page=page,
        page_size=page_size,
    )

@app.get("/opportunities/{oid}", response_model=OpportunityOut)
def get_one(oid: str, db: Session = Depends(get_db)):
    obj = db.query(models.Opportunity).filter(models.Opportunity.id == oid).one_or_none()
    if not obj:
        raise HTTPException(404, "not found")
    return obj

@app.post("/opportunities", response_model=OpportunityOut)
def create_or_update(opportunity: OpportunityIn, db: Session = Depends(get_db)):
    try:
        return crud.upsert_opportunity(db, opportunity)
    except Exception as e:
        # This makes 500s show the exact cause in the response while developing
        raise HTTPException(status_code=500, detail=str(e))

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
