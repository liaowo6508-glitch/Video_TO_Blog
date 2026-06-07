from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any, Callable

# Shared logger used across all nodes and tools for task-level visibility.
_task_logger = logging.getLogger("ai_pipeline.task")
_task_logger.setLevel(logging.INFO)
if not _task_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")
    )
    _task_logger.addHandler(handler)

# Re-export so nodes can do `from monitor import task_log`.
task_log = _task_logger.info
task_warn = _task_logger.warning
task_error = _task_logger.error


# Per-task context: tracks which task is currently executing so log lines
# can be prefixed with the task_id without passing it everywhere.
_task_context: threading.local[dict] = threading.local()


def set_task_context(task_id: str) -> None:
    _task_context.dict = {"task_id": task_id}


def clear_task_context() -> None:
    _task_context.dict = {}


def _fmt_bytes(size: float) -> str:
    if size < 1024:
        return f"{size:.0f}B"
    if size < 1024**2:
        return f"{size / 1024:.1f}KB"
    if size < 1024**3:
        return f"{size / 1024**2:.1f}MB"
    return f"{size / 1024**3:.1f}GB"


def make_progress_hook(
    label: str,
    task_id: str,
    on_complete: Callable[[], None] | None = None,
) -> Callable[[dict], None]:
    """Return a yt-dlp progress hook that emits download progress lines.

    Parameters
    ----------
    label:
        Short label for the download type (e.g. "audio", "subtitle").
    task_id:
        Current task identifier, used to prefix log lines.
    on_complete:
        Optional callback invoked when download finishes.
    """
    started_at: float | None = None

    def hook(d: dict[str, Any]) -> None:
        nonlocal started_at
        status = d.get("status", "")

        if status == "started":
            started_at = time.time()
            filename = d.get("filename", "?")
            task_log(
                "[%s] ⬇ %s 开始下载  →  %s", task_id, label, filename
            )

        elif status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)

            if total > 0:
                pct = downloaded / total * 100
                speed_str = _fmt_bytes(speed) + "/s" if speed else "?"
                eta_str = f"{eta}s" if eta else "?"
                task_log(
                    "[%s] ⬇ %s  %5.1f%%  %s/%s  @ %s  ETA %s",
                    task_id, label, pct,
                    _fmt_bytes(downloaded), _fmt_bytes(total),
                    speed_str, eta_str,
                )
            elif speed:
                speed_str = _fmt_bytes(speed) + "/s"
                task_log(
                    "[%s] ⬇ %s  %s  @ %s",
                    task_id, label, _fmt_bytes(downloaded), speed_str,
                )

        elif status == "finished":
            elapsed = time.time() - started_at if started_at else 0
            filename = d.get("filename", "?")
            task_log(
                "[%s] ✅ %s 下载完成  →  %s  (%.1fs)",
                task_id, label, filename, elapsed,
            )
            if on_complete:
                on_complete()

    return hook
