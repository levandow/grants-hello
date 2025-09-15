import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TESTING"] = "1"

from app.normalize import normalize

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
