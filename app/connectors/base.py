from typing import Iterable, Dict, Any, Protocol

class Connector(Protocol):
    def fetch(self) -> Iterable[Dict[str, Any]]:
        ...
