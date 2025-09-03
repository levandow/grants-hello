# scripts/ingest_any.py
import os, time, requests, sys
from app.normalize import normalize
from app.connectors.dummy_json import DummyJSONConnector
from app.connectors.vinnova import fetch as vinnova_fetch
from app.connectors.vinnova_rounds import fetch as vinnova_rounds_fetch
from app.connectors.eu_ftop import fetch as ftop_fetch
from app.normalize import normalize_vinnova, normalize_ftop, normalize_vinnova_round


API_URL = os.getenv("API_URL", "http://localhost:8080")

def wait_for_api(timeout=90):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{API_URL}/health", timeout=3)
            if r.ok:
                print(f"API ready at {API_URL}")
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    print(f"ERROR: API not reachable at {API_URL} within {timeout}s", file=sys.stderr)
    sys.exit(1)

def upsert(record: dict) -> None:
    n = normalize(record)
    r = requests.post(f"{API_URL}/opportunities", json=n, timeout=30)
    if r.status_code != 200:
        print(f"❌ Upsert failed [{r.status_code}] for {n.get('source_uid')}: {r.text}", file=sys.stderr)
        r.raise_for_status()
    print(f"✅ {n.get('source')}:{n.get('source_uid')}")

def main():
    wait_for_api()
    for rec in DummyJSONConnector().fetch():
        upsert(rec)
    
    #for rec in vinnova_fetch():
    #    upsert(normalize_vinnova(rec))

    for rec in vinnova_rounds_fetch():
        upsert(normalize_vinnova_round(rec))



if __name__ == "__main__":
    main()
