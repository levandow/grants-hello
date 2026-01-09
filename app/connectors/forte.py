import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

class ForteConnector:
    """
    Connector for Forte .
    """

    def __init__(self):
        self.name = "Forte"
        self.base_url = "https://api.forte.se/gdp_forte/utlysningar"

    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetches data from Forte.
        """
        api_key = os.getenv("FORTE_API_KEY")
        if not api_key:
            logger.error("Missing FORTE_API_KEY environment variable.")
            return []

        headers = {"Authorization": api_key}
        try:
            response = requests.get(self.base_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching data from {self.name}: {e}", exc_info=True)
            return []