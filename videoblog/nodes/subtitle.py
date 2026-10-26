from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from videoblog.engine.state import PipelineState
from videoblog.monitor import task_log
from videoblog.tools.subtitle_parser import process_subtitle_file
from videoblog.tools.ytdlp_tool import get_ytdlp_tool


def subtitle_node(state: PipelineState) -> PipelineState:
    """下载字幕并在临时目录中清洗，原始字幕文件不会留在 data/ 下。"""
    task_log("[%s] 进入 subtitle：下载并清洗字幕", state["task_id"])

    tool = get_ytdlp_tool()
    video_id = state.get("video_id") or state["task_id"]
    temp_dir = Path(tempfile.mkdtemp(prefix="videoblog_subs_"))
    cleaned_text: str | None = None

    try:
        subtitle_path, _ = tool.download_subtitle_text(
            state["video_url"], video_id, temp_dir
        )
        if subtitle_path:
            cleaned_text = process_subtitle_file(subtitle_path)
            task_log(
                "[%s] 字幕清洗完成，文本长度=%d",
                state["task_id"],
                len(cleaned_text),
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    has_subtitle = bool(cleaned_text)
    if not has_subtitle:
        task_log("[%s] 未获取到字幕", state["task_id"])

    return {
        **state,
        "cleaned_subtitle_text": cleaned_text,
        "has_subtitle": has_subtitle,
        "node_results": {
            **state.get("node_results", {}),
            "subtitle": {
                "has_subtitle": has_subtitle,
                "cleaned_length": len(cleaned_text or ""),
            },
        },
    }
