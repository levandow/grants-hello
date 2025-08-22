import os
import requests
from app.normalize import normalize
from app.connectors.dummy_json import DummyJSONConnector

API_URL = os.getenv("API_URL", "http://localhost:8080")

def upsert(record: dict) -> None:
    n = normalize(record)
    r = requests.post(f"{API_URL}/opportunities", json=n, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Upsert failed {n.get('source_uid')}: {r.status_code} {r.text}")
    print(f"✅ {n.get('source')}:{n.get('source_uid')}")

def main():
    # swap this connector later (e.g., VinnovaConnector, FTOPConnector)
    conn = DummyJSONConnector()
    for rec in conn.fetch():
        upsert(rec)

if __name__ == "__main__":
    main()
