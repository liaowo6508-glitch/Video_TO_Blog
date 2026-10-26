from __future__ import annotations

import logging
import sys
import threading

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
