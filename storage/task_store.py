from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from config.settings import settings
from engine.state import PipelineState


class TaskStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = settings.resolve_path(base_dir or settings.tasks_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        return self.base_dir / f"{task_id}.json"

    def save(self, state: PipelineState) -> None:
        payload = dict(state)
        self._task_path(state["task_id"]).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, task_id: str) -> PipelineState | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_tasks(self) -> list[PipelineState]:
        tasks: list[PipelineState] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        return tasks

    def create_result_file(self, task_id: str, content: str) -> str:
        output_path = settings.resolve_path(settings.results_dir) / f"{task_id}.md"
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
