import sys
import os
import logging
import json
from dotenv import load_dotenv

# Add project root to path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.connectors.formas import FormasConnector

# Configure logging to see the connector's internal logs
logging.basicConfig(level=logging.INFO)

def main():
    print("--- Testing Formas Fetch ---")

    # Load environment variables from .env file
    load_dotenv()
    
    # Check for API Key
    if not os.getenv("FORMAS_API_KEY"):
        print("WARNING: FORMAS_API_KEY environment variable is not set. Fetch may fail.")

    connector = FormasConnector()
    
    try:
        items = connector.fetch()
        print(f"Fetched {len(items)} items.")
        
        count = 0
        for item in items:
            if count >= 3:
                break
            count += 1
            
            print(f"\n--- Opportunity {count} ---")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            
        if count == 0:
            print("No items found.")

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()