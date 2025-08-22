from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import engine, get_db
from . import models, crud
from .schemas import OpportunityIn, OpportunityOut

app = FastAPI(title="Grants Hub API (Minimal)")

# Create tables on startup (kept simple; Alembic can be added later)
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
models.Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/opportunities", response_model=list[OpportunityOut])
def list_opps(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    return crud.list_opportunities(db, limit=limit, offset=offset)

@app.post("/opportunities", response_model=OpportunityOut)
def create_or_update(opportunity: OpportunityIn, db: Session = Depends(get_db)):
    return crud.upsert_opportunity(db, opportunity)

# Dev-only seeding endpoint to quickly verify the DB → API flow
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
    crud.upsert_opportunity(db, sample)
    return {"inserted": 1}
