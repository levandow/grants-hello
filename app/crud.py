from sqlalchemy.orm import Session
from . import models
from .schemas import OpportunityIn

def upsert_opportunity(db: Session, data: OpportunityIn):
    # Upsert by source_uid for idempotency
    obj = db.query(models.Opportunity).filter(models.Opportunity.source_uid == data.source_uid).one_or_none()
    payload = data.model_dump()
    if obj is None:
        obj = models.Opportunity(**payload)
        db.add(obj)
    else:
        for k, v in payload.items():
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def list_opportunities(db: Session, limit: int = 50, offset: int = 0):
    return db.query(models.Opportunity).order_by(models.Opportunity.closes_at.desc().nulls_last()).offset(offset).limit(limit).all()
