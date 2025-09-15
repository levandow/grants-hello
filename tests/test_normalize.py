import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TESTING"] = "1"

from app.normalize import normalize, normalize_ftop

def test_normalize_minimal():
    rec = {
        "id":"x1","source":"demo","source_uid":"x1",
        "title":{"en":"Title"}, "summary":{"en":"Sum"}, "status":"forthcoming",
        "links": {"landing":"https://example.org"},
        "deadlines":[{"type":"single","date":"01/12/2025"}]
    }
    n = normalize(rec)
    assert n["status"] == "planned"
    assert n["deadlines"][0]["date"] == "2025-12-01"
    assert set(n["title"].keys()) == {"sv","en"}
    assert n["topic_codes"] == []


def test_ftop_uid_fallback():
    rec = {"title": {"text": "Example"}}
    n = normalize_ftop(rec)
    assert n["source_uid"], "source_uid should not be empty"
    assert n["id"].startswith("euftop:")
    # Ensure overall normalize accepts it
    normalized = normalize(n)
    assert normalized["source_uid"] == n["source_uid"]


def test_ftop_extra_fields():
    rec = {
        "title": "Extra",
        "topicConditions": "Conditions text",
        "supportInfo": "Support text",
        "budgetOverview": "Budget text",
    }
    n = normalize_ftop(rec)
    assert n["topic_conditions"] == "Conditions text"
    assert n["support_info"] == "Support text"
    assert n["budget_overview"] == "Budget text"
