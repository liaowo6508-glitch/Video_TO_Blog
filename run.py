#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量命令行客户端：启动后进入待输入状态，直接输入视频 URL，自动构造 JSON 并调用 /tasks 接口。

用法:
    python run.py

退出:
    输入 exit、quit，或按 Ctrl+D

环境变量:
    CSDN_AUTO_PUBLISH=true  # 生成自动发布 automation_spec
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def create_task(video_url: str) -> None:
    payload: dict[str, object] = {
        "pipeline": "video_to_blog",
        "input_url": video_url,
    }
    # [CSDN发布-技术储备] publish_target 透传保留于此，待启用时取消注释并加入上方 payload 构建
    body_bytes: bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/tasks",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"任务已创建: task_id={data['task_id']}  status={data['status']}")
        print(f"查询命令: curl http://127.0.0.1:8000/tasks/{data['task_id']}")


def main() -> None:
    print("请输入视频 URL，提交后会继续等待下一条输入。")
    print("输入 exit、quit、按 Ctrl+D，或按 Ctrl+C 可退出。")

    while True:
        try:
            video_url = input("URL > ").strip()
        except EOFError:
            print("\n已退出。")
            break
        except KeyboardInterrupt:
            print("\n已退出。")
            break

        if not video_url:
            continue

        if video_url.lower() in {"exit", "quit"}:
            print("已退出。")
            break

        try:
            create_task(video_url)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"请求失败 [{e.code}]: {body}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"连接失败: {e}", file=sys.stderr)
        except Exception as e:
            print(f"发生未知错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
