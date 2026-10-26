from __future__ import annotations

from pydantic import BaseModel, Field


class Subscription(BaseModel):
    creator_uid: str
    creator_name: str
    space_url: str
    added_at: str
    last_check_at: str | None = None
    last_video_at: str | None = None
    processed_video_ids: list[str] = Field(default_factory=list)


class VideoItem(BaseModel):
    bvid: str
    title: str
    pubdate: int
    duration: str | None = None
    play: int | None = None
    pic: str | None = None
    video_url: str
