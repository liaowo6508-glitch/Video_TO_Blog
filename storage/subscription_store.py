from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from config.settings import settings
from models.schemas import Subscription


class SubscriptionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = settings.resolve_path(base_dir or settings.subscriptions_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, creator_uid: str) -> Path:
        return self.base_dir / f"{creator_uid}.json"

    def save(self, sub: Subscription) -> None:
        payload = dict(sub)
        self._task_path(sub.creator_uid).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, creator_uid: str) -> Subscription | None:
        path = self._task_path(creator_uid)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[Subscription]:
        subscriptions: list[Subscription] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            subscriptions.append(json.loads(path.read_text(encoding="utf-8")))
        return subscriptions

    def remove(self, creator_uid: str) -> bool:
        path = self._task_path(creator_uid)
        if not path.exists():
            return False
        path.unlink()
        return True

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
