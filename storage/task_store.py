from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path

from config.settings import settings
from engine.state import PipelineState


def _sanitize_filename(name: str) -> str:
    """移除文件名中的非法字符，保留中文、字母、数字、空格（替换为空格）"""
    return re.sub(r"[\\/:*?\"<>|]", "", name).strip()


def _safe_filename(name: str, max_len: int = 60) -> str:
    """将标题转换为安全的文件名，超长截断"""
    safe = _sanitize_filename(name)
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe


def _extract_article_title(blog_content: str) -> str | None:
    """从 Markdown 内容的第一行一级标题中提取文章标题"""
    match = re.search(r"^#\s+(.+)\s*$", blog_content, re.MULTILINE)
    return match.group(1).strip() if match else None


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

    def create_result_file(
        self,
        task_id: str,
        content: str,
        article_title: str | None = None,
        created_at: str | None = None,
    ) -> str:
        blogs_dir = settings.resolve_path(settings.blogs_dir)
        blogs_dir.mkdir(parents=True, exist_ok=True)

        title = article_title or _extract_article_title(content)
        ts = created_at[:10] if created_at else settings.beijing_now().strftime("%Y-%m-%d")

        if title:
            safe_title = _safe_filename(title)
            filename = f"{ts}_{safe_title}.md"
        else:
            filename = f"{ts}_{task_id}.md"

        output_path = blogs_dir / filename
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
