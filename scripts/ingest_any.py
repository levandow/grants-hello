# scripts/ingest_any.py
import os
import time
import sys
import requests
from typing import Optional

from app.normalize import normalize  # unified dispatcher
from app.connectors.dummy_json import DummyJSONConnector, DummyVinnovaConnector, DummyEUConnector
from app.connectors.vinnova import fetch as vinnova_fetch
from app.connectors.vinnova_rounds import fetch as vinnova_rounds_fetch
from app.connectors.eu_ftop import fetch as ftop_fetch
# NOTE: we no longer import per-source normalizers here; normalize() handles routing.

API_URL = os.getenv("API_URL", "http://localhost:8080")

def wait_for_api(timeout: int = 90) -> None:
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

def upsert(record: dict, *, source: Optional[str] = None, already_normalized: bool = False) -> None:
    """
    Send one opportunity to the API.
    - If already_normalized=True, 'record' is assumed to match the API schema.
    - Otherwise we normalize it here. You can pass source="VINNOVA" or "EU" to skip auto-detection.
    """
    n = record if already_normalized else normalize(record, source=source)

    r = requests.post(f"{API_URL}/opportunities", json=n, timeout=30)
    if r.status_code != 200:
        print(
            f"❌ Upsert failed [{r.status_code}] for {n.get('source')}:{n.get('source_id')}: {r.text}",
            file=sys.stderr,
        )
        r.raise_for_status()

    print(f"✅ {n.get('source')}:{n.get('source_id')}")

def main() -> None:
    wait_for_api()

    # 1) Mixed dummy JSON; let normalize() auto-detect source
    #for rec in DummyJSONConnector().fetch():
    #    upsert(rec)

    # 2) Vinnova dummy connector; route explicitly for clarity
    #for rec in DummyVinnovaConnector():
    #    upsert(rec, source="VINNOVA")

    # 3) EU dummy connector; route explicitly
    #for rec in DummyEUConnector():
    #    upsert(rec, source="EU")

    # --- Real fetchers (uncomment when needed) ---
    for rec in vinnova_rounds_fetch():
        upsert(rec, source="VINNOVA")
    
    for rec in ftop_fetch():
        upsert(rec, source="EU")

if __name__ == "__main__":
    main()