from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from config.settings import settings
from engine.registry import PipelineRegistry
from engine.state import PipelineState, PipelineStatus
from monitor import clear_task_context, set_task_context, task_error, task_log
from storage.task_store import TaskStore


class PipelineRunner:
    def __init__(self, task_store: TaskStore | None = None) -> None:
        self.task_store = task_store or TaskStore()

    def create_initial_state(
        self,
        pipeline: str,
        video_url: str,
        task_id: str | None = None,
        publish_target: str | None = None,
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
            publish_target=publish_target,
            publish_status=None,
            publish_url=None,
            publish_payload=None,
            publish_mode=None,
            task_dir=f"{settings.beijing_now().strftime('%Y%m%d_%H%M%S')}_{task_id}",
        )

    def run(
        self,
        pipeline: str,
        video_url: str,
        task_id: str | None = None,
        publish_target: str | None = None,
    ) -> PipelineState:
        state = self.create_initial_state(
            pipeline,
            video_url,
            task_id=task_id,
            publish_target=publish_target,
        )
        self.task_store.save(state)
        set_task_context(state["task_id"])
        task_log("[%s] 任务已创建 pipeline=%s", state["task_id"], pipeline)

        try:
            graph = PipelineRegistry.get(pipeline)
            running_state = {
                **state,
                "status": PipelineStatus.RUNNING,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.task_store.save(running_state)
            task_log("[%s] 开始执行流水线", state["task_id"])
            result = graph.invoke(running_state)
            final_state = {
                **result,
                "status": PipelineStatus.SUCCEEDED,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.task_store.save(final_state)
            task_log("[%s] 任务成功完成", state["task_id"])
            return final_state
        except Exception as exc:
            latest_state = self.task_store.get(state["task_id"]) or state
            failed_state = {
                **latest_state,
                "status": PipelineStatus.FAILED,
                "error": str(exc),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.task_store.save(failed_state)
            task_error("[%s] 任务失败: %s", state["task_id"], exc)
            return failed_state
        finally:
            clear_task_context()
