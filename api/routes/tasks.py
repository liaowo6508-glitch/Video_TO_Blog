from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from engine.registry import PipelineRegistry
from engine.runner import PipelineRunner
from models.schemas import TaskRead, TaskRequest, TaskResponse
from storage.task_store import TaskStore

router = APIRouter(prefix="/tasks", tags=["tasks"])
task_store = TaskStore()
runner = PipelineRunner(task_store=task_store)


def _run_pipeline_task(
    task_id: str,
    pipeline: str,
    input_url: str,
    publish_target: str | None,
) -> None:
    runner.run(
        pipeline=pipeline,
        video_url=input_url,
        task_id=task_id,
        publish_target=publish_target,
    )


@router.post("", response_model=TaskResponse)
def create_task(req: TaskRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    if req.pipeline not in PipelineRegistry.list_names():
        raise HTTPException(status_code=404, detail="Unknown pipeline")

    initial_state = runner.create_initial_state(
        req.pipeline,
        req.get_url(),
        publish_target=req.publish_target,
    )
    task_store.save(initial_state)
    background_tasks.add_task(
        _run_pipeline_task,
        initial_state["task_id"],
        req.pipeline,
        req.get_url(),
        req.publish_target,
    )

    return TaskResponse(
        task_id=initial_state["task_id"],
        status=initial_state["status"],
        created_at=initial_state["created_at"],
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str) -> TaskRead:
    state = task_store.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRead.model_validate(state)


@router.get("", response_model=list[TaskRead])
def list_tasks() -> list[TaskRead]:
    return [TaskRead.model_validate(item) for item in task_store.list_tasks()]
