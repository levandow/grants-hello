# app/connectors/eu_ftop.py
from __future__ import annotations
import logging
import requests
import json
from typing import Iterator, Dict, Any

logger = logging.getLogger(__name__)

API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY = "SEDIA"

# Constants for EU API filter values
STATUS_FORTHCOMING = "31094501"  # Forthcoming grant calls
STATUS_OPEN = "31094502"  # Open grant calls
FRAMEWORK_HORIZON_EUROPE = "43108390"  # Horizon Europe programme
PROGRAMME_PERIOD = "2021 - 2027"
CALL_TYPES = ["1"]  # calls/topics (1=Grants)

# Filters: open grant calls under Horizon Europe, status OPEN
# See examples in public threads and EC pages; adjust as needed.
QUERY = {
    "bool": {
        "must": [
            {"terms": {"type": CALL_TYPES}},
            {"terms": {"status": [STATUS_FORTHCOMING, STATUS_OPEN]}}
        ]
    }
}
SORT = {"field": "sortStatus", "order": "ASC"}

def fetch(page_size: int = 100, max_pages: int | None = None) -> Iterator[Dict[str, Any]]:
    """
    Fetch open grant calls from the EU Funding & Tenders Portal API.

    Iterates through pages of results, yielding individual grant call records.
    Stops early if an empty page is encountered or if an error occurs.

    Args:
        page_size: Number of results per page (default: 100, max supported by API is likely 100)
        max_pages: Maximum number of pages to fetch. If None, fetches until no more results.

    Yields:
        Dictionary containing grant call metadata for each result

    Raises:
        requests.RequestException: If API request fails after logging the error
    """
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        try:
            logger.info(f"Fetching page {page}/{max_pages if max_pages else '?'} with page_size={page_size}")

            # Parameters passed in URL
            params = {
                "apiKey": API_KEY,
                "text": "***",
                "pageSize": page_size,
                "pageNumber": page,
            }
            
            # Use 'files' to force a multipart/form-data request, which matches Postman's behavior.
            # 'query' is sent as a file upload (with filename and content-type).
            files = {
                "query": ("CS.json", json.dumps(QUERY), "application/json"),
            }

            r = requests.post(
                API,
                params=params,
                files=files,
                timeout=40,
            )
            r.raise_for_status()
            data = r.json()

            if page == 1 and isinstance(data, dict):
                logger.info(f"Total results available according to API: {data.get('totalResults', 'unknown')}")

            items: list[Any] = []
            if isinstance(data, dict):
                if isinstance(data.get("results"), list):
                    items = data["results"]
                else:
                    # Some responses wrap the actual hits inside ``resultList``
                    rl = data.get("resultList")
                    if isinstance(rl, dict):
                        if isinstance(rl.get("results"), list):
                            items = rl["results"]
                        elif isinstance(rl.get("result"), list):
                            items = rl["result"]

            if not items:
                logger.info(f"No items found on page {page}, stopping pagination")
                break

            logger.info(f"Retrieved {len(items)} items from page {page}")
            for rec in items:
                # Client-side check to ensure we only output Open or Forthcoming calls
                metadata = rec.get("metadata", {})
                statuses = metadata.get("status") or []
                
                # 1. Check top-level status (fast check)
                if not any(s in [STATUS_FORTHCOMING, STATUS_OPEN] for s in statuses):
                    ident = metadata.get("identifier", ["Unknown"])[0] if metadata.get("identifier") else "Unknown"
                    logger.info(f"Skipping item {ident} with status {statuses}")
                    continue

                # 2. Check detailed 'actions' status (deep check, source of truth)
                actions_raw = metadata.get("actions")
                if actions_raw and isinstance(actions_raw, list):
                    found_any_status = False
                    found_open_status = False
                    
                    for action_str in actions_raw:
                        if not isinstance(action_str, str):
                            continue
                        try:
                            actions_data = json.loads(action_str)
                            if isinstance(actions_data, list):
                                for action in actions_data:
                                    st_id = str(action.get("status", {}).get("id", ""))
                                    if st_id:
                                        found_any_status = True
                                        if st_id in [STATUS_FORTHCOMING, STATUS_OPEN]:
                                            found_open_status = True
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    # If we successfully parsed statuses, but none were Open/Forthcoming, skip the item.
                    if found_any_status and not found_open_status:
                        ident = metadata.get("identifier", ["Unknown"])[0] if metadata.get("identifier") else "Unknown"
                        logger.info(f"Skipping item {ident}: Deep check found no open actions.")
                        continue

                yield rec

        except requests.Timeout:
            logger.error(f"Request timeout on page {page} after 40 seconds")
            break
        except requests.RequestException as e:
            logger.error(f"Failed to fetch page {page}: {e}")
            if isinstance(e, requests.HTTPError) and e.response is not None:
                logger.error(f"API Response: {e.response.text}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response on page {page}: {e}")
            break
        page += 1
