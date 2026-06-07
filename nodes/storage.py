from __future__ import annotations

from engine.state import PipelineState, PipelineStatus
from monitor import task_log
from storage.task_store import TaskStore


def storage_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 storage：落盘结果", state["task_id"])
    task_store = TaskStore()
    blog_content = state.get("blog_content")
    if not blog_content:
        raise ValueError("No blog content available to store")

    output_path = task_store.create_result_file(state["task_id"], blog_content)
    task_log("[%s] 结果文件已写入: %s", state["task_id"], output_path)
    return {
        **state,
        "output_path": output_path,
        "status": PipelineStatus.SUCCEEDED,
        "node_results": {
            **state.get("node_results", {}),
            "storage": {
                "output_path": output_path,
            },
        },
    }
