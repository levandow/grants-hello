from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class OpportunityIn(BaseModel):
    id: str
    source: str
    source_uid: str
    title: Dict[str, Optional[str]]
    summary: Dict[str, Optional[str]]
    programme: Optional[str] = None
    sponsor: Optional[str] = None
    tags: List[str] = []
    deadlines: List[dict] = []
    status: str
    links: dict
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    notes: Optional[str] = None

class OpportunityOut(OpportunityIn):
    pass
