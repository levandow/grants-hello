import json
from pathlib import Path
from typing import Iterable, Dict, Any, Iterator, List, Union
import re


class DummyJSONConnector:
    def __init__(self, path: str = "scripts/sample_data.json"):
        self.path = Path(path)

    def fetch(self) -> Iterable[Dict[str, Any]]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for rec in data:
            yield rec

class DummyVinnovaConnector:
    def __init__(self, path: str = "scripts/vinnova_sample_data.json"):
        self.path = Path(path)

    def fetch(self) -> Iterator[Dict[str, Any]]:
        """
        The endpoint commonly supports incremental by date, sometimes with simple pagination.
        We try date-first; if the API doesn’t page, we’ll just return the whole list.
        """
        with self.path.open() as fp:
            data = json.load(fp)

        if isinstance(data, list):
            for x in data:
                yield x
            return

        items = data.get("results") or data.get("Result") or data.get("data") or []
        for x in items:
            yield x
        
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self.fetch()

class DummyEUConnector:
    def __init__(self, path: str = "scripts/eu_sample_data.json"):
        self.path = Path(path)

    def _load_json_resilient(self) -> Union[Dict[str, Any], List[Any]]:
        """
        Load JSON from file, fixing common issues:
        - Stray backslashes (Invalid \\escape)
        - JSON Lines (NDJSON) fallback
        """
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except json.JSONDecodeError:
            # Retry with cleanup: escape stray backslashes not part of valid escapes
            text = self.path.read_text(encoding="utf-8")

            # First attempt: escape any backslash that isn't followed by a valid JSON escape char
            # Valid escapes are: " \ / b f n r t u
            fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                # NDJSON/JSONL fallback: parse line by line
                items: List[Any] = []
                for ln in text.splitlines():
                    s = ln.strip()
                    if not s:
                        continue
                    try:
                        items.append(json.loads(s))
                    except json.JSONDecodeError:
                        # last-ditch fix for a line with stray backslashes
                        s_fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)
                        items.append(json.loads(s_fixed))
                return items

    def fetch(self) -> Iterator[Dict[str, Any]]:
        data = self._load_json_resilient()

        # Normalize to a list of records
        items: List[Any] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if isinstance(data.get("results"), list):
                items = data["results"]
            else:
                rl = data.get("resultList")
                if isinstance(rl, dict):
                    if isinstance(rl.get("results"), list):
                        items = rl["results"]
                    elif isinstance(rl.get("result"), list):
                        items = rl["result"]

        for rec in items:
            # Ensure each yielded item is a dict, skip otherwise
            if isinstance(rec, dict):
                yield rec

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self.fetch()
