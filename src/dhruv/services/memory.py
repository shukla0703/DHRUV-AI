from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from src.dhruv.config import settings


@dataclass
class MemoryEvent:
    timestamp: str
    category: str
    query: str
    detail: str


class MemoryStore:
    def __init__(self) -> None:
        self.path = Path(settings.memory_store_path)
        self.limit = max(settings.memory_store_limit, 10)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, category: str, query: str, detail: str) -> None:
        event = MemoryEvent(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            category=category,
            query=query.strip(),
            detail=detail.strip(),
        )
        payload = self._load()
        payload.append(asdict(event))
        payload = payload[-self.limit :]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def recent(self, category: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        payload = self._load()
        if category:
            payload = [item for item in payload if item.get("category") == category]
        return payload[-limit:]

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        return []
