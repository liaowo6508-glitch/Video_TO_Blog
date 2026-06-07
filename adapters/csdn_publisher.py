# [CSDN发布-技术储备]
# ---------------------------------------------------------------------------
# 本文件已注释，待启用时取消整个文件注释。
# 该文件依赖 Cursor MCP 浏览器工具执行自动化发布操作。
# 启用前需确保 cursor-ide-browser MCP server 已启用且用户已登录 CSDN。
# ---------------------------------------------------------------------------
# from __future__ import annotations
#
# from pathlib import Path
#
# from adapters.csdn_formatter import format_csdn_payload
# from config.settings import settings
#
# CSDN_EDITOR_URL = "https://editor.csdn.net/mdeditor"
#
#
# def _build_browser_automation_spec(
#     title: str,
#     body: str,
#     summary: str,
#     tags: list[str],
#     editor_url: str,
# ) -> dict[str, object]:
#     return {
#         "server": "cursor-ide-browser",
#         "preconditions": [
#             "用户已在 Cursor 内置浏览器登录 CSDN",
#             "编辑页可访问，且未被验证码或弹窗阻塞",
#         ],
#         "target_url": editor_url,
#         "steps": [
#             {
#                 "action": "navigate",
#                 "url": editor_url,
#                 "description": "打开 CSDN Markdown 编辑页",
#             },
#             {
#                 "action": "fill",
#                 "field": "title",
#                 "value": title,
#                 "description": "填写文章标题",
#             },
#             {
#                 "action": "fill",
#                 "field": "body_markdown",
#                 "value": body,
#                 "description": "填写 Markdown 正文",
#             },
#             {
#                 "action": "fill",
#                 "field": "summary",
#                 "value": summary,
#                 "description": "填写摘要",
#             },
#             {
#                 "action": "fill_tags",
#                 "field": "tags",
#                 "value": tags,
#                 "description": "填写文章标签",
#             },
#             {
#                 "action": "select",
#                 "field": "content_type",
#                 "value": "original",
#                 "description": "选择原创文章",
#             },
#             {
#                 "action": "click",
#                 "field": "publish_button",
#                 "description": "点击发布按钮",
#             },
#             {
#                 "action": "capture_result",
#                 "field": "article_url",
#                 "description": "发布成功后记录最终文章 URL",
#             },
#         ],
#         "notes": [
#             "不同账号或页面版本下，标签/摘要/发布按钮的选择器可能不同，需要在 MCP 浏览器执行时根据 snapshot 动态定位。",
#             "若出现专栏、封面、可见范围等额外弹窗，应优先保留默认值并继续完成发布。",
#         ],
#     }
#
#
# def publish_csdn(
#     markdown_file: str,
#     csdn_editor_url: str | None = None,
#     auto_publish: bool | None = None,
# ) -> dict[str, object]:
#     payload = format_csdn_payload(Path(markdown_file))
#     editor_url = csdn_editor_url or settings.csdn_editor_url or CSDN_EDITOR_URL
#     resolved_auto_publish = settings.csdn_auto_publish if auto_publish is None else auto_publish
#
#     result: dict[str, object] = {
#         "status": "ready",
#         "mode": "auto" if resolved_auto_publish else "manual",
#         "editor_url": editor_url,
#         "payload": payload.to_dict(),
#         "instructions": [
#             f"在浏览器中打开 {editor_url}",
#             f"标题输入框填入：{payload.title}",
#             f"标签输入框填入：{', '.join(payload.tags)}",
#             f"摘要输入框填入：{payload.summary}",
#             "正文编辑器粘贴 Markdown 正文",
#             "文章类型选择为原创",
#             "点击发布并记录最终文章 URL",
#         ],
#     }
#
#     if resolved_auto_publish:
#         result["automation_spec"] = _build_browser_automation_spec(
#             title=payload.title,
#             body=payload.body,
#             summary=payload.summary,
#             tags=payload.tags,
#             editor_url=editor_url,
#         )
#         result["status"] = "automation_ready"
#
#     return result
