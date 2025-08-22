import json
from pathlib import Path
from typing import Iterable, Dict, Any

class DummyJSONConnector:
    def __init__(self, path: str = "scripts/sample_data.json"):
        self.path = Path(path)

    def fetch(self) -> Iterable[Dict[str, Any]]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for rec in data:
            yield rec
