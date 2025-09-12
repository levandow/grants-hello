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
    programme: Optional[str] = None
    sponsor: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    status: str
    links: Links = Field(default_factory=Links)
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="ignore")  # ignore any unexpected top-level props

class Deadline(BaseModel):
    type: str
    date: str

class OpportunityOut(BaseModel):
    id: str
    source: str
    source_uid: str
    title: LocalizedText
    summary: LocalizedText
    programme: Optional[str] = None
    sponsor: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    status: str
    links: Links
    opens_at: Optional[date] = None
    closes_at: Optional[date] = None
    notes: Optional[str] = None


class Facets(BaseModel):
    sponsors: List[str] = Field(default_factory=list)
    programmes: List[str] = Field(default_factory=list)
    statuses: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
