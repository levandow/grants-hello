import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

class FormasConnector:
    """
    Connector for Formas (Swedish Research Council for Sustainable Development).
    """

    def __init__(self):
        self.name = "Formas"
        self.base_url = "https://api.formas.se/gdp_formas/utlysningar"

    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetches data from Formas.
        """
        api_key = os.getenv("FORMAS_API_KEY")
        if not api_key:
            logger.error("Missing FORMAS_API_KEY environment variable.")
            return []

        headers = {"Authorization": api_key}
        try:
            response = requests.get(self.base_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching data from {self.name}: {e}", exc_info=True)
            return []