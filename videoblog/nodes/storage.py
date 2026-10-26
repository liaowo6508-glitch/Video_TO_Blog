from __future__ import annotations

from videoblog.engine.state import PipelineState, PipelineStatus
from videoblog.monitor import task_log
from videoblog.storage.output_store import save_blog


def storage_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 storage：保存博客", state["task_id"])
    blog_content = state.get("blog_content")
    if not blog_content:
        raise ValueError("No blog content available to store")

    output_path = save_blog(
        task_id=state["task_id"],
        content=blog_content,
        article_title=state.get("article_title"),
        created_at=state.get("created_at"),
    )
    task_log("[%s] 博客已写入: %s", state["task_id"], output_path)

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
