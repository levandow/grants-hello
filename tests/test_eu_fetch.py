import sys
import os
import logging
import json

# Add project root to path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.connectors.eu_ftop import fetch
from app.normalize import normalize_eu

# Configure logging to see the connector's internal logs
logging.basicConfig(level=logging.INFO)

def main():
    print("--- Testing EU FTOP Fetch & Normalize ---")
    count = 0
    try:
        # Fetch a small batch to test normalization
        for i, item in enumerate(fetch(page_size=10, max_pages=1)):
            if count >= 3:
                break

            count += 1
            normalized = normalize_eu(item)
            
            # Omit the large raw JSON blob for readability in the console
            if "extra_json" in normalized:
                normalized["extra_json"] = "(omitted for brevity)"

            print(f"\n--- Opportunity {count} [{normalized.get('id')}] ---")
            print(json.dumps(normalized, indent=2, ensure_ascii=False))
            
        if count == 0:
            print("No items found matching the criteria.")

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()