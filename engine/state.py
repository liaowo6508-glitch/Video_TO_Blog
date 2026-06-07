from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PipelineState(TypedDict, total=False):
    task_id: str
    video_url: str
    pipeline_type: str
    created_at: str
    updated_at: str

    video_id: str | None
    task_dir: str | None
    video_title: str
    video_path: str | None
    subtitle_path: str | None
    audio_path: str | None
    transcript: str | None
    source_text: str | None
    blog_content: str | None
    article_title: str | None
    output_path: str | None

    has_subtitle: bool
    status: PipelineStatus
    error: str | None
    node_results: dict[str, Any]
