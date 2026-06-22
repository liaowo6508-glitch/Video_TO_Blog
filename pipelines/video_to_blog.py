from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from debug_utils import debug_log

# #region agent log
try:
    debug_log(
        location="pipelines/video_to_blog.py:8",
        message="video_to_blog module import started",
        data={"imports": ["engine.registry", "engine.state", "nodes.*"]},
        hypothesis_id="H4",
    )
except Exception:
    pass
# #endregion
from engine.registry import PipelineRegistry
from engine.state import PipelineState
from nodes.ingest import ingest_node
from nodes.llm import llm_node
from nodes.storage import storage_node
from nodes.subtitle import subtitle_node
from nodes.subtitle_clean import subtitle_clean_node


@PipelineRegistry.register("video_to_blog")
def video_to_blog_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("subtitle_clean", subtitle_clean_node)
    graph.add_node("llm", llm_node)
    graph.add_node("storage", storage_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "subtitle")
    graph.add_edge("subtitle", "subtitle_clean")
    graph.add_edge("subtitle_clean", "llm")
    graph.add_edge("llm", "storage")
    graph.add_edge("storage", END)
    return graph.compile()
