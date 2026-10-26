from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from videoblog.engine.registry import PipelineRegistry
from videoblog.engine.state import PipelineState, PipelineStatus
from videoblog.monitor import clear_task_context, set_task_context, task_error, task_log


class PipelineRunner:
    def create_initial_state(
        self,
        pipeline: str,
        video_url: str,
        task_id: str | None = None,
    ) -> PipelineState:
        timestamp = datetime.now(timezone.utc).isoformat()
        task_id = task_id or str(uuid4())
        return PipelineState(
            task_id=task_id,
            video_url=video_url,
            pipeline_type=pipeline,
            created_at=timestamp,
            updated_at=timestamp,
            status=PipelineStatus.PENDING,
            error=None,
            node_results={},
            has_subtitle=False,
        )

    def run(
        self,
        pipeline: str,
        video_url: str,
        task_id: str | None = None,
    ) -> PipelineState:
        state = self.create_initial_state(pipeline, video_url, task_id=task_id)
        set_task_context(state["task_id"])
        task_log("[%s] 任务已创建 pipeline=%s", state["task_id"], pipeline)

        try:
            graph = PipelineRegistry.get(pipeline)
            task_log("[%s] 开始执行流水线", state["task_id"])
            result = graph.invoke(
                {
                    **state,
                    "status": PipelineStatus.RUNNING,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            task_log("[%s] 任务成功完成", state["task_id"])
            return {
                **result,
                "status": PipelineStatus.SUCCEEDED,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            task_error("[%s] 任务失败: %s", state["task_id"], exc)
            return {
                **state,
                "status": PipelineStatus.FAILED,
                "error": str(exc),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            clear_task_context()
