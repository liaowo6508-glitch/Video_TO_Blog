#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量命令行客户端：只需传入视频 URL，自动构造 JSON 并调用 /tasks 接口。

用法:
    python run.py "https://www.bilibili.com/video/BV1xx411c7mD"
    python run.py "https://www.bilibili.com/video/BV1xx411c7mD" --publish csdn

环境变量:
    CSDN_AUTO_PUBLISH=true  # 生成自动发布 automation_spec
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建 video_to_blog 任务")
    parser.add_argument("video_url", help="视频 URL")
    # [CSDN发布-技术储备] --publish csdn 参数保留于此，待启用时取消注释
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload: dict[str, object] = {
        "pipeline": "video_to_blog",
        "input_url": args.video_url,
    }
    # [CSDN发布-技术储备] publish_target 透传保留于此，待启用时取消注释并加入上方 payload 构建
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
