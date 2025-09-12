import os
from datetime import date
from typing import Optional, List

from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from .db import engine, get_db
from . import models, crud
from .schemas import OpportunityIn, OpportunityOut
try:
    # Pydantic v2
    from pydantic import BaseModel, Field, ConfigDict
    V2 = True
except Exception:
    # Pydantic v1 fallback
    from pydantic import BaseModel, Field
    class _Cfg: ...
    ConfigDict = _Cfg  # dummy
    V2 = False


# --------------------------- app & startup ---------------------------



app = FastAPI(title="Grants Hub API (Minimal)")

# --- CORS (dev-friendly; tighten in production) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # replace with exact domain(s) when deploying
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB objects and indexes on startup (simple path; Alembic can be added later)
if os.getenv("TESTING") != "1":
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[startup] DB init skipped or failed: {e}")

    try:
        with engine.begin() as conn:
            # Scalar indexes to accelerate filters/sorting
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_status ON opportunities (status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_sponsor ON opportunities (sponsor);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_programme ON opportunities (programme);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_closes_at ON opportunities (closes_at);"))
            # Functional indexes over JSON text for lightweight search
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_title_en   ON opportunities ((title->>'en'));"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_summary_en ON opportunities ((summary->>'en'));"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_title_sv   ON opportunities ((title->>'sv'));"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_opps_summary_sv ON opportunities ((summary->>'sv'));"))
        print("[startup] Index checks complete")
    except Exception as e:
        print(f"[startup] Index creation skipped: {e}")


# --------------------------- health ---------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------- list/search ---------------------------

class OpportunitiesResponse(BaseModel):
    items: List[OpportunityOut] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    if V2:
        model_config = ConfigDict(extra="ignore")
    else:
        class Config:
            extra = "ignore"

@app.get("/opportunities", response_model=OpportunitiesResponse)
def list_opps(
    q: Optional[str] = Query(None, description="Free text query"),
    query: Optional[str] = Query(None, description="Alias for q"),
    sponsor: Optional[str] = None,
    programme: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = Query(None, description="Match a tag string"),
    deadline_after: Optional[str] = Query(None, description="YYYY-MM-DD"),
    deadline_before: Optional[str] = Query(None, description="YYYY-MM-DD"),
    sort: str = Query("recent", description="recent | deadline_asc | deadline_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Paged list with filters. Returns {"items":[...], "total":N, "page":x, "page_size":y}.
    Accepts both ?q= and ?query= for convenience.
    """
    try:
        term = q or query
        rows, total = crud.search_opportunities(
            db,
            q=term,
            status=status,
            sponsor=sponsor,
            programme=programme,
            tag=tag,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        # Serialize ORM → schema (ensures clean JSON)
        items = [
            OpportunityOut.model_validate(o, from_attributes=True).model_dump()
            for o in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------- get one ---------------------------

@app.get("/opportunities/{oid}", response_model=OpportunityOut)
def get_one(oid: str, db: Session = Depends(get_db)):
    obj = db.query(models.Opportunity).filter(models.Opportunity.id == oid).one_or_none()
    if not obj:
        raise HTTPException(404, "not found")
    return OpportunityOut.model_validate(obj, from_attributes=True)


# --------------------------- upsert ---------------------------

@app.post("/opportunities", response_model=OpportunityOut)
def create_or_update(opportunity: OpportunityIn, db: Session = Depends(get_db)):
    try:
        obj = crud.upsert_opportunity(db, opportunity)
        return OpportunityOut.model_validate(obj, from_attributes=True)
    except Exception as e:
        # During development, expose the exact cause to the client
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------- dev seed ---------------------------

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
        deadlines=[{"type": "single", "date": "2025-12-01"}],
        status="open",
        links={"landing": "https://example.org"},
        opens_at="2025-10-01",
        closes_at="2025-12-01",
    )
    obj = crud.upsert_opportunity(db, sample)
    return {"inserted": 1, "id": obj.id}
