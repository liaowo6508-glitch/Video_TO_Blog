from __future__ import annotations

from pathlib import Path

from engine.state import PipelineState
from monitor import task_log
from tools.llm_tool import get_llm


BLOG_SYSTEM_PROMPT = """你是一名中文技术内容编辑。请将输入内容整理成结构清晰、适合发布的中文博客文章。要求：
1. 输出 Markdown。
2. 自动提炼标题、摘要、小节结构。
3. 保留关键信息和时间顺序。
4. 如果是口语化转写，转换为书面表达。
5. 在结尾补充“总结”小节。"""


def llm_node(state: PipelineState) -> PipelineState:
    task_log("[%s] 进入 llm：生成博客", state["task_id"])
    source_text = state.get("transcript")
    if not source_text and state.get("subtitle_path"):
        source_text = Path(state["subtitle_path"]).read_text(encoding="utf-8")

    if not source_text:
        raise ValueError("No source text available for blog generation")

    prompt = (
        f"请将以下视频内容整理为一篇结构化中文博客文章。\\n\\n"
        f"视频标题：{state.get('video_title', '未命名视频')}\\n"
        f"来源链接：{state['video_url']}\\n\\n"
        f"内容如下：\\n{source_text}"
    )
    content = get_llm().generate(prompt=prompt, system=BLOG_SYSTEM_PROMPT)
    task_log("[%s] LLM 完成，内容长度=%s", state["task_id"], len(content))

    return {
        **state,
        "source_text": source_text,
        "blog_content": content,
        "node_results": {
            **state.get("node_results", {}),
            "llm": {
                "content_length": len(content),
            },
        },
    }
