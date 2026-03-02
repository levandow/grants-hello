import os
from datetime import date, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

from . import crud, models, security
from .db import create_all, get_db
from .schemas import OpportunityIn, OpportunityOut, Facets, User, UserCreate, Token, TokenData, Technology, TechnologyCreate
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
create_all()


app = FastAPI(title="Grants Hub API (Minimal)")

# --- CORS ---
# Set CORS_ORIGINS in env as a comma-separated list, e.g.:
#   CORS_ORIGINS=https://app.example.com,https://admin.example.com
# Defaults to localhost dev ports. Wildcard "*" disables credentials.
_cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
_allow_credentials = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --------------------------- auth & users ---------------------------

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/users/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# --------------------------- technologies ---------------------------

@app.post("/technologies/", response_model=Technology)
def create_technology(
    technology: TechnologyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.create_technology(db=db, technology=technology, user_id=current_user.id)


@app.get("/technologies/", response_model=List[Technology])
def read_technologies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    technologies = crud.get_technologies_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return technologies

# --------------------------- health ---------------------------

@app.get("/health")
def health():
    return {"status": "ok"}



@app.get("/facets", response_model=Facets)
def facets(db: Session = Depends(get_db)):
    return crud.get_facets(db)

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
    id: Optional[str] = Query(None, description="Filter by ID"),
    title: Optional[str] = Query(None, description="Filter by title text"),
    summary: Optional[str] = Query(None, description="Filter by summary text"),
    description: Optional[str] = Query(None, description="Filter by description text"),
    source: Optional[str] = None,
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
            id=id,
            title=title,
            summary=summary,
            description=description,
            source=source,
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
        items = []
        for o in rows:
            base = OpportunityOut.model_validate(o, from_attributes=True).model_dump()
            if getattr(o, "extra", None):
                base.update(o.extra)
            items.append(base)
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------- get one ---------------------------

@app.get("/opportunities/{oid}", response_model=OpportunityOut)
def get_one(oid: str, db: Session = Depends(get_db)):
    obj = db.query(models.Opportunity).filter(models.Opportunity.id == oid).one_or_none()
    if not obj:
        raise HTTPException(404, "not found")
    base = OpportunityOut.model_validate(obj, from_attributes=True).model_dump()
    if getattr(obj, "extra", None):
        base.update(obj.extra)
    return base


# --------------------------- upsert ---------------------------

@app.post("/opportunities", response_model=OpportunityOut)
def create_or_update(opportunity: OpportunityIn, db: Session = Depends(get_db)):
    try:
        obj = crud.upsert_opportunity(db, opportunity)
        base = OpportunityOut.model_validate(obj, from_attributes=True).model_dump()
        if getattr(obj, "extra", None):
            base.update(obj.extra)
        return base
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
