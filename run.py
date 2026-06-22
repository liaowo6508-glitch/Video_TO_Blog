#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量命令行客户端：启动后进入待输入状态，直接输入视频 URL，自动构造 JSON 并调用 /tasks 接口。

用法:
    python run.py [--port PORT] [--host HOST] [--pipeline PIPELINE] [--poll]

选项:
    -p, --port PORT      服务器端口号 (默认: 8000)
    -H, --host HOST      服务器地址 (默认: 127.0.0.1)
    --pipeline PIPELINE  流水线名称 (默认: subtitle_only)
                        - subtitle_only: 仅下载并清洗字幕，返回文档地址
                        - video_to_blog: 完整视频转博客流程
    --poll               提交后自动轮询直到任务完成，并输出文档地址
    -h, --help           显示帮助信息

退出:
    输入 exit、quit，或按 Ctrl+D

环境变量:
    CSDN_AUTO_PUBLISH=true  # 生成自动发布 automation_spec
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="视频 URL 输入工具，支持字幕下载或视频转博客任务。",
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
    parser.add_argument(
        "--pipeline",
        type=str,
        default="subtitle_only",
        dest="pipeline",
        choices=["subtitle_only", "video_to_blog"],
        help="流水线名称 (默认: subtitle_only)",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        dest="poll",
        help="提交后自动轮询直到任务完成，并输出文档地址",
    )
    parser.add_argument(
        "--no-poll",
        action="store_false",
        dest="poll",
        help="提交后立即返回，不轮询",
    )
    parser.set_defaults(poll=False)
    return parser.parse_args()


def create_task(video_url: str, host: str, port: int, pipeline: str) -> dict:
    base_url = f"http://{host}:{port}"
    payload: dict[str, object] = {
        "pipeline": pipeline,
        "input_url": video_url,
    }
    body_bytes: bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/tasks",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data


def poll_task(base_url: str, task_id: str, max_wait: int = 300) -> dict:
    """轮询任务状态直到完成，返回最终状态"""
    elapsed = 0
    interval = 2
    while elapsed < max_wait:
        with urllib.request.urlopen(f"{base_url}/tasks/{task_id}") as resp:
            state = json.loads(resp.read().decode("utf-8"))
            status = state.get("status", "unknown")
            if status in ("succeeded", "failed"):
                return state
        time.sleep(interval)
        elapsed += interval
    return {"status": "timeout", "task_id": task_id}


def print_result(state: dict, pipeline: str) -> None:
    """根据流水线类型输出结果"""
    status = state.get("status", "unknown")
    task_id = state.get("task_id", "?")

    if status == "succeeded":
        if pipeline == "subtitle_only":
            doc_path = state.get("subtitle_document_path", "")
            if doc_path:
                print(f"字幕文档地址: {doc_path}")
            subtitle_path = state.get("subtitle_path", "")
            if subtitle_path:
                print(f"原始字幕文件: {subtitle_path}")
        elif pipeline == "video_to_blog":
            output_path = state.get("output_path", "")
            if output_path:
                print(f"博客文档地址: {output_path}")
        print(f"任务完成: task_id={task_id} status={status}")
    elif status == "failed":
        error = state.get("error", "未知错误")
        print(f"任务失败: task_id={task_id} error={error}")
    else:
        print(f"任务状态: task_id={task_id} status={status}")


def main() -> None:
    args = parse_args()
    base_url = f"http://{args.host}:{args.port}"

    print(f"流水线: {args.pipeline}")
    print(f"轮询: {'开启' if args.poll else '关闭'}")
    print(f"当前连接: {base_url}")
    print("请输入视频 URL，提交后会继续等待下一条输入。")
    print("输入 exit、quit、按 Ctrl+D，或按 Ctrl+C 可退出。")

    while True:
        try:
            video_url = input("\nURL > ").strip()
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
            result = create_task(video_url, args.host, args.port, args.pipeline)
            task_id = result["task_id"]
            print(f"任务已创建: task_id={task_id}  status={result['status']}")
            print(f"查询命令: curl {base_url}/tasks/{task_id}")

            if args.poll:
                print("正在轮询任务状态...")
                final_state = poll_task(base_url, task_id)
                print_result(final_state, args.pipeline)

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"请求失败 [{e.code}]: {body}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"连接失败: {e}", file=sys.stderr)
        except Exception as e:
            print(f"发生未知错误: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
