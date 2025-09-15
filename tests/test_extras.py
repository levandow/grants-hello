import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TESTING"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, crud
from app.schemas import OpportunityIn, OpportunityOut

def get_session():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_upsert_and_serialize_extras():
    db = get_session()
    data = OpportunityIn(
        id="e1",
        source="s",
        source_uid="e1",
        title={"en": "t"},
        summary={"en": "s"},
        status="open",
        links={"landing": ""},
        topic_conditions="c1",
        support_info="s1",
        budget_overview="b1",
    )
    obj = crud.upsert_opportunity(db, data)
    assert obj.extra["topic_conditions"] == "c1"
    out = OpportunityOut.model_validate(obj, from_attributes=True).model_dump()
    out.update(obj.extra)
    assert out["support_info"] == "s1"
