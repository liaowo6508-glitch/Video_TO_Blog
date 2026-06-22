from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from config.settings import settings
from models.schemas import VideoItem


class VideoStore:
    """持久化存储每个 UP 主 discover 到的视频，便于去重和历史查看。"""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = settings.resolve_path(base_dir or settings.videos_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, creator_uid: str) -> Path:
        return self.base_dir / f"{creator_uid}.json"

    def _load_raw(self, creator_uid: str) -> list[dict]:
        path = self._path(creator_uid)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def load(self, creator_uid: str) -> list[VideoItem]:
        """加载指定 UP 主的已发现视频列表，按 pubdate 降序。"""
        raw = self._load_raw(creator_uid)
        videos = [VideoItem(**v) for v in raw]
        videos.sort(key=lambda v: v.pubdate, reverse=True)
        return videos

    def save(self, creator_uid: str, videos: list[VideoItem]) -> None:
        """保存（覆盖）指定 UP 主的视频列表。"""
        path = self._path(creator_uid)
        path.write_text(
            json.dumps([v.model_dump(mode="json") for v in videos], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert(self, creator_uid: str, new_videos: list[VideoItem]) -> list[VideoItem]:
        """将新视频合并到已有列表，按 pubdate 降序返回完整列表。"""
        existing = {v.bvid: v for v in self._load_raw(creator_uid)}
        for v in new_videos:
            existing[v.bvid] = v
        merged = sorted(existing.values(), key=lambda v: v.pubdate, reverse=True)
        self.save(creator_uid, merged)
        return merged

    def list_by_uid(self, creator_uid: str, limit: int | None = None) -> list[VideoItem]:
        """返回指定 UP 主的视频列表，可选 limit。"""
        videos = self.load(creator_uid)
        return videos[:limit] if limit else videos
