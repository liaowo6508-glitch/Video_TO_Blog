#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量命令行客户端：只需传入视频 URL，自动构造 JSON 并调用 /tasks 接口。

用法:
    python run.py "https://www.bilibili.com/video/BV1xx411c7mD"
"""

from __future__ import annotations

import json
import sys
import urllib.request


def main() -> None:
    if len(sys.argv) != 2:
        print(f"用法: python {sys.argv[0]} <视频URL>")
        sys.exit(1)

    video_url: str = sys.argv[1]
    payload: dict = {
        "pipeline": "video_to_blog",
        "input_url": video_url,
    }

    body_bytes: bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/tasks",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"任务已创建: task_id={data['task_id']}  status={data['status']}")
            print(f"查询命令: curl http://127.0.0.1:8000/tasks/{data['task_id']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"请求失败 [{e.code}]: {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
