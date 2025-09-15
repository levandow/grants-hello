import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TESTING"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, crud


def get_session():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_get_facets():
    db = get_session()
    o1 = models.Opportunity(
        id="1",
        source="s",
        source_uid="1",
        title={"en": "t"},
        summary={"en": "s"},
        programme="p1",
        sponsor="a1",
        topic_codes=[],
        tags=["t1", "t2"],
        deadlines=[],
        status="open",
        links={"landing": ""},
    )
    o2 = models.Opportunity(
        id="2",
        source="s",
        source_uid="2",
        title={"en": "t"},
        summary={"en": "s"},
        programme="p2",
        sponsor="a2",
        topic_codes=[],
        tags=["t2"],
        deadlines=[],
        status="closed",
        links={"landing": ""},
    )
    db.add_all([o1, o2])
    db.commit()

    facets = crud.get_facets(db)
    assert facets["sponsors"] == ["a1", "a2"]
    assert facets["programmes"] == ["p1", "p2"]
    assert facets["statuses"] == ["closed", "open"]
    assert facets["tags"] == ["t1", "t2"]

