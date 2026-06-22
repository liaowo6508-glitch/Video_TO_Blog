from __future__ import annotations

import re

from config.settings import settings
from engine.state import PipelineState, PipelineStatus
from monitor import task_log


def subtitle_store_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 subtitle_store：保存字幕文档", state["task_id"])

    subtitles_dir = settings.resolve_path(settings.subtitles_dir)
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    video_title = state.get("video_title", "unknown")
    safe_title = _sanitize_filename(video_title)
    task_id = state.get("task_id", "")
    filename = f"{safe_title}_{task_id}.txt"
    output_path = subtitles_dir / filename

    if not state.get("has_subtitle"):
        task_log("[%s] 无字幕，仅保存任务信息", state["task_id"])
        content = f"视频标题: {video_title}\n视频URL: {state.get('video_url', '')}\n字幕: 无可用字幕"
    else:
        content = state.get("cleaned_subtitle_text", "")

    output_path.write_text(content, encoding="utf-8")
    task_log("[%s] 字幕文档已写入: %s", state["task_id"], output_path)

    return {
        **state,
        "subtitle_document_path": str(output_path),
        "status": PipelineStatus.SUCCEEDED,
        "node_results": {
            **state.get("node_results", {}),
            "subtitle_store": {
                "document_path": str(output_path),
                "has_subtitle": state.get("has_subtitle", False),
            },
        },
    }


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "", name).strip()
