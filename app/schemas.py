from typing import Any, Dict, List, Optional
from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class Links(BaseModel):
    landing: str = ""                 # required by your JSON Schema, default empty string
    model_config = ConfigDict(extra="allow")  # <— accept extra keys like 'guidelines'

class LocalizedText(BaseModel):
    sv: Optional[str] = None
    en: Optional[str] = None

class Deadline(BaseModel):
    type: str
    date: str

class OpportunityIn(BaseModel):
    id: str
    source: str
    source_uid: str
    title: LocalizedText
    summary: LocalizedText
    description: Optional[LocalizedText] = None
    programme: Optional[str] = None
    sponsor: Optional[str] = None
    topic_codes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    status: str
    links: Links = Field(default_factory=Links)
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # accept and preserve unknown fields

class OpportunityOut(BaseModel):
    id: str
    source: str
    source_uid: str
    title: LocalizedText
    summary: LocalizedText
    description: Optional[LocalizedText] = None
    programme: Optional[str] = None
    sponsor: Optional[str] = None
    topic_codes: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    status: str
    links: Links
    opens_at: Optional[date] = None
    closes_at: Optional[date] = None
    notes: Optional[str] = None
    model_config = ConfigDict(extra="allow")

class Facets(BaseModel):
    sponsors: List[str] = Field(default_factory=list)
    programmes: List[str] = Field(default_factory=list)
    statuses: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)

class TechnologyBase(BaseModel):
    name: str
    description: Optional[str] = None
    trl: Optional[int] = Field(default=None, ge=1, le=9, description="Technology Readiness Level (1-9)")

class TechnologyCreate(TechnologyBase):
    pass

class Technology(TechnologyBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    technologies: List[Technology] = []

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
