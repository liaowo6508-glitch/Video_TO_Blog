from __future__ import annotations

from engine.state import PipelineState
from monitor import task_log
from tools.asr_tool import get_asr
from tools.ytdlp_tool import get_ytdlp_tool


def asr_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 asr：下载音频并转写", state["task_id"])
    tool = get_ytdlp_tool()
    asr_service = get_asr()

    task_dir = state.get("task_dir") or state["task_id"]
    video_id: str = state.get("video_id") or state["task_id"]
    url = state["video_url"]

    audio_path = tool.download_audio_only(url, video_id, task_dir)
    transcript = asr_service.transcribe(audio_path)
    task_log("[%s] ASR 完成，转写长度=%s", state["task_id"], len(transcript))

    return {
        **state,
        "audio_path": audio_path,
        "transcript": transcript,
        "source_text": transcript,
        "node_results": {
            **state.get("node_results", {}),
            "asr": {
                "audio_path": audio_path,
                "transcript_length": len(transcript),
            },
        },
    }
