from __future__ import annotations

import re
from pathlib import Path

from config.prompts import get_prompt_config
from engine.state import PipelineState
from monitor import task_log
from tools.llm_tool import get_llm


def _extract_article_title(blog_content: str) -> str | None:
    match = re.search(r"^#\s+(.+)\s*$", blog_content, re.MULTILINE)
    return match.group(1).strip() if match else None


def llm_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 llm：生成博客", state["task_id"])

    source_text = state.get("cleaned_subtitle_text") or state.get("transcript")
    if not source_text and state.get("subtitle_path"):
        source_text = Path(state["subtitle_path"]).read_text(encoding="utf-8")

    if not source_text:
        raise ValueError("No source text available for blog generation")

    cfg = get_prompt_config()

    user_prompt = cfg.user_template.format(
        video_title=state.get("video_title", "未命名视频"),
        video_url=state["video_url"],
        source_text=source_text,
    )

    content = get_llm().generate(
        prompt=user_prompt,
        system=cfg.system_prompt,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        json_mode=(cfg.output_format.type == "json"),
        json_schema=cfg.output_format.json_schema,
    )

    task_log("[%s] LLM 完成，内容长度=%s", state["task_id"], len(content))

    article_title = _extract_article_title(content)
    if article_title:
        task_log("[%s] 文章标题已提取: %s", state["task_id"], article_title)

    return {
        **state,
        "source_text": source_text,
        "blog_content": content,
        "article_title": article_title,
        "node_results": {
            **state.get("node_results", {}),
            "llm": {
                "content_length": len(content),
                "output_format": cfg.output_format.type,
                "article_title": article_title,
            },
        },
    }
