import os
from fastapi import FastAPI, Depends
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities", response_model=list[OpportunityOut])
def list_opps(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    return crud.list_opportunities(db, limit=limit, offset=offset)

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
