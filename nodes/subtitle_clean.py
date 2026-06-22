from __future__ import annotations

from pathlib import Path

from engine.state import PipelineState
from monitor import task_log
from tools.subtitle_parser import process_subtitle_file


def subtitle_clean_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 subtitle_clean：清洗字幕时间戳", state["task_id"])

    subtitle_path = state.get("subtitle_path")
    if not subtitle_path:
        raise ValueError("No subtitle_path found in state")

    if not Path(subtitle_path).exists():
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

    include_time = state.get("include_subtitle_time", False)
    cleaned_text = process_subtitle_file(subtitle_path, include_time=include_time)

    task_log("[%s] 字幕清洗完成，文本长度=%d", state["task_id"], len(cleaned_text))

    return {
        **state,
        "cleaned_subtitle_text": cleaned_text,
        "node_results": {
            **state.get("node_results", {}),
            "subtitle_clean": {
                "original_path": subtitle_path,
                "include_time": include_time,
                "cleaned_length": len(cleaned_text),
            },
        },
    }
