from __future__ import annotations

from pathlib import Path

from engine.state import PipelineState
from monitor import task_log
from tools.ytdlp_tool import get_ytdlp_tool


def ingest_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 ingest：抓取元信息", state["task_id"])
    tool = get_ytdlp_tool()
    info = tool.extract_info(state["video_url"])

    video_title = info.get("title", "unknown") if info else "unknown"
    video_id = info.get("id", state.get("task_id", "unknown")) if info else state.get(
        "task_id", "unknown"
    )

    return {
        **state,
        "video_title": video_title,
        "video_id": video_id,
        "node_results": {
            **state.get("node_results", {}),
            "ingest": {
                "video_title": video_title,
                "video_id": video_id,
            },
        },
    }
