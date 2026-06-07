from __future__ import annotations

from engine.state import PipelineState
from monitor import task_log
from storage.task_store import TaskStore
from tools.ytdlp_tool import get_ytdlp_tool


def subtitle_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 subtitle：优先尝试字幕", state["task_id"])
    tool = get_ytdlp_tool()
    task_store = TaskStore()

    task_dir = state.get("task_dir") or state["task_id"]
    video_id: str = state.get("video_id") or state["task_id"]
    url = state["video_url"]

    subtitle_path, downloaded = tool.download_subtitle_text(url, video_id, task_dir)
    has_subtitle = subtitle_path is not None
    next_state = {
        **state,
        "subtitle_path": subtitle_path,
        "has_subtitle": has_subtitle,
        "node_results": {
            **state.get("node_results", {}),
            "subtitle": {
                "has_subtitle": has_subtitle,
                "subtitle_path": subtitle_path,
                "downloaded": downloaded,
            },
        },
    }
    task_store.save(next_state)

    if has_subtitle:
        task_log("[%s] 字幕可用，跳过 ASR", state["task_id"])
    else:
        task_log("[%s] 未获取到字幕，转入 ASR", state["task_id"])

    return next_state
