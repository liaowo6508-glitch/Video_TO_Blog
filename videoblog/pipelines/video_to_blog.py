from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from videoblog.engine.registry import PipelineRegistry
from videoblog.engine.state import PipelineState
from videoblog.nodes.ingest import ingest_node
from videoblog.nodes.llm import llm_node
from videoblog.nodes.storage import storage_node
from videoblog.nodes.subtitle import subtitle_node
from videoblog.nodes.subtitle_store import subtitle_store_node


def route_after_subtitle(state: PipelineState) -> str:
    return "subtitle_store" if state.get("has_subtitle") else "no_subtitle"


def no_subtitle_node(state: PipelineState) -> PipelineState:
    raise ValueError(
        "未获取到字幕，无法生成博客。请检查 config.ini 中的 B站 cookie，"
        "或改用 --pipeline subtitle_only。"
    )


@PipelineRegistry.register("video_to_blog")
def video_to_blog_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("subtitle_store", subtitle_store_node)
    graph.add_node("no_subtitle", no_subtitle_node)
    graph.add_node("llm", llm_node)
    graph.add_node("storage", storage_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "subtitle")
    graph.add_conditional_edges(
        "subtitle",
        route_after_subtitle,
        {
            "subtitle_store": "subtitle_store",
            "no_subtitle": "no_subtitle",
        },
    )
    graph.add_edge("no_subtitle", END)
    graph.add_edge("subtitle_store", "llm")
    graph.add_edge("llm", "storage")
    graph.add_edge("storage", END)
    return graph.compile()
