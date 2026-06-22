from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from storage.subscription_store import SubscriptionStore
from tools.bilibili_discovery import discover_new_videos
from models.schemas import Subscription, VideoItem


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
store = SubscriptionStore()


class SubscriptionCreateRequest(BaseModel):
    creator_uid: str = Field(..., description="B站 UID")
    creator_name: str = Field(..., description="博主名称")
    space_url: str | None = Field(default=None, description="博主空间页 URL")


class SubscriptionRead(BaseModel):
    creator_uid: str
    creator_name: str
    space_url: str | None
    added_at: str
    last_check_at: str | None
    last_video_at: str | None
    processed_video_ids: list[str]


class DiscoverAllResponse(BaseModel):
    discovered: dict[str, list[dict[str, Any]]]


@router.post("", response_model=SubscriptionRead)
def create_subscription(req: SubscriptionCreateRequest) -> SubscriptionRead:
    existing = store.get(req.creator_uid)
    if existing:
        return SubscriptionRead(**existing)

    sub = Subscription(
        creator_uid=req.creator_uid,
        creator_name=req.creator_name,
        space_url=req.space_url or f"https://space.bilibili.com/{req.creator_uid}",
        added_at=datetime.now(timezone.utc).isoformat(),
    )
    store.save(sub)
    return SubscriptionRead(**dict(sub))


@router.get("", response_model=list[SubscriptionRead])
def list_subscriptions() -> list[SubscriptionRead]:
    return [SubscriptionRead(**dict(sub)) for sub in store.list_all()]


@router.delete("/{creator_uid}")
def delete_subscription(creator_uid: str) -> dict[str, bool]:
    removed = store.remove(creator_uid)
    if not removed:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"removed": True}


@router.post("/{creator_uid}/discover", response_model=list[VideoItem])
def discover_subscription(creator_uid: str, max_items: int = 10) -> list[VideoItem]:
    sub = store.get(creator_uid)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    videos, _ = discover_new_videos(
        sub=sub,
        creator_uid=creator_uid,
        max_items=max_items,
    )
    store.save(Subscription(**sub))
    return videos


@router.post("/discover-all", response_model=DiscoverAllResponse)
def discover_all(max_items: int = 10) -> DiscoverAllResponse:
    result: dict[str, list[dict[str, Any]]] = {}
    for sub in store.list_all():
        try:
            videos, _ = discover_new_videos(
                sub=dict(sub),
                creator_uid=sub["creator_uid"],
                max_items=max_items,
            )
            store.save(Subscription(**sub))
        except Exception as exc:
            from monitor import task_warn
            task_warn("discover-all 失败: uid=%s error=%s", sub["creator_uid"], exc)
            videos = []
        result[sub["creator_uid"]] = [video.model_dump(mode="json") for video in videos]
    return DiscoverAllResponse(discovered=result)
