from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import settings
from monitor import task_log, task_warn
from models.schemas import VideoItem
from storage.video_store import VideoStore
import yt_dlp


def _build_cookie_file() -> str | None:
    """构造 Netscape 格式 cookie 文件路径，供 yt-dlp 复用其 B站 WBI 处理逻辑。"""
    cookie_file = settings.bilibili_cookie_file
    if cookie_file:
        resolved = settings.resolve_path(cookie_file)
        if resolved.exists():
            return str(resolved)

    cookies = settings.bilibili_sessdata
    if cookies:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        tmp.write("# Netscape HTTP Cookie File\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t{cookies}\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tb_lsid\t8A1B2C3D4E5F6G7H\t\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tDedeUserID\t\t\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tDedeUserID__ckMd5\t\t\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tBILI_JCT\t\t\n")
        tmp.write(f".bilibili.com\tTRUE\t/\tFALSE\t0\tbuvid3\t\t\n")
        tmp.close()
        task_log("🍪 discovery 创建临时 cookie 文件: %s", tmp.name)
        return tmp.name

    return None


def fetch_up_videos(uid: str, ps: int = 10) -> list[VideoItem]:
    """调用 B站创作中心 API 获取 UP主最新视频列表，按发布时间倒序。

    通过 yt-dlp 调用 space 页，利用其内置的 WBI 签名和完整 cookie 处理
    （BUVID3 + BILI_JCT + SESSDATA）绕过 -403 权限限制。
    """
    space_url = f"https://space.bilibili.com/{uid}/video"

    cookie_file = _build_cookie_file()
    should_delete_cookie = cookie_file is not None and cookie_file.startswith(
        tempfile.gettempdir()
    )

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
        "playlist_items": f"1:{ps}",
        "http_headers": {
            "User-Agent": settings.yt_dlp_user_agent,
            "Referer": "https://www.bilibili.com/",
        },
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file

    task_log("discovery 请求 UP主空间视频: uid=%s url=%s", uid, space_url)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(space_url, download=False)
    except Exception as exc:
        task_warn("discovery yt-dlp 提取失败: uid=%s error=%s", uid, exc)
        raise RuntimeError(f"B站 API 提取失败: {exc}") from exc
    finally:
        if should_delete_cookie and cookie_file and os.path.exists(cookie_file):
            try:
                os.unlink(cookie_file)
            except OSError:
                pass

    if info is None:
        return []

    entries = info.get("entries") or []
    if not isinstance(entries, list):
        return []

    items: list[VideoItem] = []
    for video in entries:
        bvid = str(video.get("display_id") or video.get("id") or "")
        if not bvid or bvid == "None":
            continue
        items.append(
            VideoItem(
                bvid=bvid,
                title=str(video.get("title", "")),
                pubdate=int(video.get("timestamp") or 0),
                duration=str(video.get("duration", "") or ""),
                play=video.get("view_count") if isinstance(video.get("view_count"), int) else None,
                pic=str(video.get("thumbnail") or "") or None,
                video_url=f"https://www.bilibili.com/video/{bvid}",
            )
        )

    items.sort(key=lambda item: item.pubdate, reverse=True)
    task_log("discovery 获取成功: uid=%s count=%d", uid, len(items))
    return items


def discover_new_videos(
    sub: dict | None = None,
    *,
    creator_uid: str,
    creator_name: str | None = None,
    last_check_at: str | None = None,
    last_video_at: str | None = None,
    processed_video_ids: list[str] | None = None,
    max_items: int = 10,
) -> tuple[list[VideoItem], str | None]:
    """拉取 UP 主最新视频，返回新增的视频列表。

    去重权威来源：VideoStore（data/videos/<uid>.json）。
    processed_video_ids / last_video_at 参数仅用于兼容旧订阅记录，
    不再参与去重逻辑。sub 中的对应字段会在本次执行后同步更新。
    """
    video_store = VideoStore()
    persisted: list[VideoItem] = video_store.load(creator_uid)
    persisted_bvids: set[str] = {v.bvid for v in persisted}

    fetched = fetch_up_videos(creator_uid, ps=max_items)
    new_videos: list[VideoItem] = []

    for video in fetched:
        if video.bvid in persisted_bvids:
            continue
        new_videos.append(video)

    if new_videos:
        video_store.upsert(creator_uid, new_videos)
        task_log("discovery 新增视频: uid=%s count=%d bvid=%s",
                 creator_uid, len(new_videos), [v.bvid for v in new_videos])

    now_iso = datetime.now(timezone.utc).isoformat()
    latest_ts: int | None = _to_ts(last_video_at)
    for video in fetched:
        if latest_ts is None or video.pubdate > latest_ts:
            latest_ts = video.pubdate

    if sub is not None:
        sub["last_check_at"] = now_iso
        if latest_ts:
            sub["last_video_at"] = datetime.fromtimestamp(latest_ts, tz=timezone.utc).isoformat()
        sub.setdefault("processed_video_ids", [])
        for video in new_videos:
            if video.bvid not in sub["processed_video_ids"]:
                sub["processed_video_ids"].append(video.bvid)

    return new_videos, now_iso


def _to_ts(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except Exception:
        return None
