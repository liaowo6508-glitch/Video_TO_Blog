#!/usr/bin/env python3
"""B站 UP 主订阅管理（直接运行，无需后端服务）。

用法:
    python subscriptions.py add <UID> --name "UP名"
    python subscriptions.py list
    python subscriptions.py remove <UID>
    python subscriptions.py discover <UID> [--max 10] [--to-blog]
    python subscriptions.py discover-all [--max 10] [--to-blog]

订阅记录保存在 data/subscriptions/，已发现的视频保存在 data/videos/。
"""

from __future__ import annotations

import argparse
import sys

from videoblog.config.settings import settings
from videoblog.engine.runner import PipelineRunner
from videoblog.models.subscription import Subscription, VideoItem
from videoblog.storage.subscription_store import SubscriptionStore
from videoblog.storage.video_store import VideoStore
from videoblog.tools.bilibili_discovery import discover_new_videos


def _setup_console() -> None:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def _print_videos(videos: list[VideoItem]) -> None:
    if not videos:
        print("  没有新视频。")
        return
    for video in videos:
        print(f"  {video.bvid}  {video.title}")
        print(f"    {video.video_url}")


def _to_blog(videos: list[VideoItem]) -> None:
    if not videos:
        return
    runner = PipelineRunner()
    for video in videos:
        print(f"\n>>> 转为博客: {video.title}")
        state = runner.run(pipeline="video_to_blog", video_url=video.video_url)
        status = state.get("status", "unknown")
        status = status.value if hasattr(status, "value") else str(status)
        if status == "succeeded":
            print(f"    博客: {state.get('output_path')}")
        else:
            print(f"    失败: {state.get('error')}")


def cmd_add(args: argparse.Namespace) -> int:
    store = SubscriptionStore()
    existing = store.get(args.uid)
    if existing:
        print(f"已存在订阅: {existing.get('creator_name')} ({args.uid})")
        return 0
    sub = Subscription(
        creator_uid=args.uid,
        creator_name=args.name or args.uid,
        space_url=args.space_url or f"https://space.bilibili.com/{args.uid}",
        added_at=store.now(),
    )
    store.save(sub)
    print(f"已添加订阅: {sub.creator_name} ({sub.creator_uid})")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    subs = SubscriptionStore().list_all()
    if not subs:
        print("暂无订阅。")
        return 0
    video_store = VideoStore()
    for sub in subs:
        count = len(video_store.list_by_uid(sub["creator_uid"]))
        print(
            f"{sub['creator_uid']}  {sub['creator_name']}  "
            f"已记录视频={count}  上次检查={sub.get('last_check_at') or '从未'}"
        )
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    if SubscriptionStore().remove(args.uid):
        print(f"已删除订阅: {args.uid}")
        return 0
    print(f"未找到订阅: {args.uid}")
    return 1


def _discover_one(store: SubscriptionStore, sub: dict, max_items: int) -> list[VideoItem]:
    print(f"\n检查 {sub['creator_name']} ({sub['creator_uid']}) ...")
    try:
        videos, _ = discover_new_videos(
            sub=sub,
            creator_uid=sub["creator_uid"],
            max_items=max_items,
        )
    except Exception as exc:
        print(f"  拉取失败: {exc}")
        return []
    store.save(sub)
    _print_videos(videos)
    return videos


def cmd_discover(args: argparse.Namespace) -> int:
    store = SubscriptionStore()
    sub = store.get(args.uid)
    if not sub:
        print(f"未找到订阅: {args.uid}，请先执行 add。")
        return 1
    videos = _discover_one(store, sub, args.max)
    if args.to_blog:
        _to_blog(videos)
    return 0


def cmd_discover_all(args: argparse.Namespace) -> int:
    store = SubscriptionStore()
    subs = store.list_all()
    if not subs:
        print("暂无订阅。")
        return 0
    all_new: list[VideoItem] = []
    for sub in subs:
        all_new.extend(_discover_one(store, sub, args.max))
    if args.to_blog:
        _to_blog(all_new)
    return 0


def main() -> int:
    _setup_console()
    settings.ensure_directories()

    parser = argparse.ArgumentParser(
        description="B站 UP 主订阅管理（直接运行，无需服务）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="添加订阅")
    add.add_argument("uid", help="UP 主 UID")
    add.add_argument("--name", help="UP 主名称（默认使用 UID）")
    add.add_argument("--space-url", help="空间地址（默认按 UID 生成）")
    add.set_defaults(func=cmd_add)

    list_cmd = subparsers.add_parser("list", help="列出订阅")
    list_cmd.set_defaults(func=cmd_list)

    remove = subparsers.add_parser("remove", help="删除订阅")
    remove.add_argument("uid", help="UP 主 UID")
    remove.set_defaults(func=cmd_remove)

    discover = subparsers.add_parser("discover", help="检查单个 UP 主的新视频")
    discover.add_argument("uid", help="UP 主 UID")
    discover.add_argument("--max", type=int, default=10, help="最多拉取视频数（默认 10）")
    discover.add_argument("--to-blog", action="store_true", help="把新视频直接转为博客")
    discover.set_defaults(func=cmd_discover)

    discover_all = subparsers.add_parser("discover-all", help="检查全部订阅")
    discover_all.add_argument("--max", type=int, default=10, help="每个 UP 最多拉取视频数（默认 10）")
    discover_all.add_argument("--to-blog", action="store_true", help="把新视频直接转为博客")
    discover_all.set_defaults(func=cmd_discover_all)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
