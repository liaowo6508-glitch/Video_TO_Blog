#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量命令行客户端：启动后进入待输入状态，直接输入视频 URL，自动构造 JSON 并调用 /tasks 接口。

用法:
    python run.py [--port PORT] [--host HOST]

选项:
    -p, --port PORT  服务器端口号 (默认: 8000)
    -H, --host HOST  服务器地址 (默认: 127.0.0.1)
    -h, --help       显示帮助信息

退出:
    输入 exit、quit，或按 Ctrl+D

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
    parser = argparse.ArgumentParser(
        description="视频 URL 输入工具，向 /tasks 接口提交视频转博客任务。",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        dest="port",
        help="服务器端口号 (默认: 8000)",
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default="127.0.0.1",
        dest="host",
        help="服务器地址 (默认: 127.0.0.1)",
    )
    return parser.parse_args()


def create_task(video_url: str, host: str, port: int) -> None:
    base_url = f"http://{host}:{port}"
    payload: dict[str, object] = {
        "pipeline": "video_to_blog",
        "input_url": video_url,
    }
    # [CSDN发布-技术储备] publish_target 透传保留于此，待启用时取消注释并加入上方 payload 构建
    body_bytes: bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/tasks",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"任务已创建: task_id={data['task_id']}  status={data['status']}")
        print(f"查询命令: curl {base_url}/tasks/{data['task_id']}")


def main() -> None:
    args = parse_args()
    print("请输入视频 URL，提交后会继续等待下一条输入。")
    print("输入 exit、quit、按 Ctrl+D，或按 Ctrl+C 可退出。")
    print(f"当前连接: http://{args.host}:{args.port}")

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
            create_task(video_url, args.host, args.port)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"请求失败 [{e.code}]: {body}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"连接失败: {e}", file=sys.stderr)
        except Exception as e:
            print(f"发生未知错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
