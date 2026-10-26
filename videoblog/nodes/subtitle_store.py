from __future__ import annotations

from videoblog.engine.state import PipelineState, PipelineStatus
from videoblog.monitor import task_log
from videoblog.storage.output_store import save_subtitle


def subtitle_store_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 subtitle_store：保存清洗后字幕", state["task_id"])

    video_title = state.get("video_title", "unknown")
    if not state.get("has_subtitle"):
        task_log("[%s] 无字幕，仅保存任务信息", state["task_id"])
        content = (
            f"视频标题: {video_title}\n"
            f"视频URL: {state.get('video_url', '')}\n"
            "字幕: 无可用字幕"
        )
    else:
        content = state.get("cleaned_subtitle_text", "")

    output_path = save_subtitle(
        task_id=state.get("task_id", ""),
        video_title=video_title,
        content=content,
    )
    task_log("[%s] 字幕文档已写入: %s", state["task_id"], output_path)

    return {
        **state,
        "subtitle_document_path": output_path,
        "status": PipelineStatus.SUCCEEDED,
        "node_results": {
            **state.get("node_results", {}),
            "subtitle_store": {
                "document_path": output_path,
                "has_subtitle": state.get("has_subtitle", False),
            },
        },
    }
