from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from engine.state import PipelineStatus


class TaskRequest(BaseModel):
    pipeline: str = Field(..., description="Pipeline name, e.g. video_to_blog")
    input_url: str | None = None
    video_url: str | None = None
    publish_target: str | None = Field(default=None, description="Publish target platform, e.g. 'csdn'")
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_url(self) -> "TaskRequest":
        if not self.input_url and not self.video_url:
            raise ValueError("Either 'input_url' or 'video_url' must be provided")
        if self.input_url and self.video_url:
            raise ValueError("Only one of 'input_url' or 'video_url' may be provided")
        return self

    def get_url(self) -> str:
        return self.input_url or self.video_url or ""


class TaskResponse(BaseModel):
    task_id: str
    status: PipelineStatus
    created_at: datetime


class TaskRead(BaseModel):
    task_id: str
    video_url: str
    pipeline_type: str
    created_at: datetime
    updated_at: datetime
    status: PipelineStatus
    error: str | None = None
    video_id: str | None = None
    task_dir: str | None = None
    video_title: str | None = None
    video_path: str | None = None
    subtitle_path: str | None = None
    audio_path: str | None = None
    transcript: str | None = None
    source_text: str | None = None
    blog_content: str | None = None
    output_path: str | None = None
    publish_target: str | None = None
    publish_status: str | None = None
    publish_url: str | None = None
    publish_mode: str | None = None
    publish_payload: dict[str, Any] | None = None
    has_subtitle: bool = False
    node_results: dict[str, Any] = Field(default_factory=dict)
