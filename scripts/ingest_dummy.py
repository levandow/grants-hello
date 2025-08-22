import json
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8080")

def ingest(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        opportunities = json.load(f)

    for opp in opportunities:
        r = requests.post(f"{API_URL}/opportunities", json=opp)
        if r.status_code == 200:
            print(f"✅ Ingested {opp['id']}")
        else:
            print(f"❌ Failed {opp['id']} → {r.status_code}: {r.text}")

if __name__ == "__main__":
    ingest("scripts/sample_data.json")
