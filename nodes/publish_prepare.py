# [CSDN发布-技术储备]
# ---------------------------------------------------------------------------
# 本文件已注释，待启用时：
#   1. 取消 settings.py 中的 csdn_* 配置注释
#   2. 恢复 adapters/csdn_publisher.py 和 adapters/csdn_formatter.py
#   3. 恢复 nodes/publish_prepare.py
#   4. 恢复 pipelines/video_to_blog.py 中的 publish_prepare 节点接入
#   5. 恢复 run.py 中的 --publish 参数
#   6. 恢复 engine/state.py、models/schemas.py、engine/runner.py、api/routes/tasks.py 中的 publish_* 字段
# ---------------------------------------------------------------------------
# from __future__ import annotations
#
# from pathlib import Path
#
# from adapters.csdn_publisher import publish_csdn
# from config.settings import settings
# from engine.state import PipelineState
# from monitor import task_error, task_log
#
#
# def publish_prepare_node(state: PipelineState) -> PipelineState:
#     task_id = state["task_id"]
#     publish_target = state.get("publish_target")
#
#     if not publish_target:
#         task_log("[%s] 未配置 publish_target，跳过发布准备", task_id)
#         return state
#
#     output_path = state.get("output_path")
#     if not output_path or not Path(output_path).exists():
#         task_error("[%s] 博客文件不存在，无法发布: %s", task_id, output_path)
#         return {
#             **state,
#             "publish_status": "skipped",
#             "node_results": {
#                 **state.get("node_results", {}),
#                 "publish_prepare": {
#                     "status": "skipped",
#                     "reason": "output_path_missing",
#                 },
#             },
#         }
#
#     if publish_target != "csdn":
#         task_error("[%s] 未知 publish_target: %s", task_id, publish_target)
#         return {
#             **state,
#             "publish_status": "failed",
#             "node_results": {
#                 **state.get("node_results", {}),
#                 "publish_prepare": {
#                     "status": "failed",
#                     "reason": f"unknown_target:{publish_target}",
#                 },
#             },
#         }
#
#     task_log("[%s] 进入 publish_prepare：生成 CSDN 发布 payload", task_id)
#     result = publish_csdn(
#         output_path,
#         csdn_editor_url=settings.csdn_editor_url,
#         auto_publish=settings.csdn_auto_publish,
#     )
#     payload = result.get("payload", {})
#     return {
#         **state,
#         "publish_status": str(result.get("status", "ready")),
#         "publish_mode": str(result.get("mode", "manual")),
#         "publish_payload": result,
#         "node_results": {
#             **state.get("node_results", {}),
#             "publish_prepare": {
#                 "status": result.get("status", "ready"),
#                 "mode": result.get("mode", "manual"),
#                 "target": "csdn",
#                 "editor_url": result.get("editor_url"),
#                 "title": payload.get("title") if isinstance(payload, dict) else None,
#                 "tags": payload.get("tags") if isinstance(payload, dict) else None,
#                 "has_automation_spec": "automation_spec" in result,
#             },
#         },
#     }
