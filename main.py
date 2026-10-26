#!/usr/bin/env python3
"""直接运行入口：无需启动后端服务。

用法:
    python main.py                             # 交互式输入 URL
    python main.py <URL> [<URL> ...]           # 处理一个或多个 URL
    python main.py <URL> --pipeline subtitle_only

配置:
    用记事本修改项目根目录的 config.ini（B站 cookie、DeepSeek Key、模型等）。
"""

from __future__ import annotations

import argparse
import sys

from videoblog.config.settings import settings
from videoblog.engine.runner import PipelineRunner
from videoblog.engine.state import PipelineState
import videoblog.pipelines  # noqa: F401  注册流水线


PIPELINES = ["video_to_blog", "subtitle_only"]


def _setup_console() -> None:
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def _status_value(state: PipelineState) -> str:
    status = state.get("status", "unknown")
    return status.value if hasattr(status, "value") else str(status)


def _print_result(state: PipelineState) -> bool:
    status = _status_value(state)
    task_id = state.get("task_id", "?")

    if status == "succeeded":
        output_path = state.get("output_path")
        if output_path:
            print(f"博客文档: {output_path}")
        subtitle_doc = state.get("subtitle_document_path")
        if subtitle_doc:
            print(f"字幕文档: {subtitle_doc}")
        print(f"完成: task_id={task_id}")
        return True

    print(f"失败: task_id={task_id}")
    print(f"原因: {state.get('error')}")
    return False


def _run_one(runner: PipelineRunner, url: str, pipeline: str) -> bool:
    print(f"\n>>> 开始处理 [{pipeline}]: {url}")
    state = runner.run(pipeline=pipeline, video_url=url)
    return _print_result(state)


def _interactive(runner: PipelineRunner, pipeline: str) -> int:
    print(f"流水线: {pipeline}")
    print("输入视频 URL 回车执行；输入 exit / quit 退出。")
    ok = True
    while True:
        try:
            url = input("\nURL > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break
        if not url:
            continue
        if url.lower() in {"exit", "quit"}:
            print("已退出。")
            break
        ok = _run_one(runner, url, pipeline) and ok
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="视频转博客 / B站字幕下载（直接运行，无需服务）")
    parser.add_argument("urls", nargs="*", help="视频 URL；不传则进入交互模式")
    parser.add_argument(
        "--pipeline",
        default=settings.default_pipeline,
        choices=PIPELINES,
        help=f"流水线（默认: {settings.default_pipeline}）",
    )
    args = parser.parse_args()

    _setup_console()
    runner = PipelineRunner()

    if args.urls:
        results = [_run_one(runner, url, args.pipeline) for url in args.urls]
        return 0 if all(results) else 1
    return _interactive(runner, args.pipeline)


if __name__ == "__main__":
    raise SystemExit(main())
