from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from videoblog.engine.registry import PipelineRegistry
from videoblog.engine.state import PipelineState
from videoblog.nodes.ingest import ingest_node
from videoblog.nodes.subtitle import subtitle_node
from videoblog.nodes.subtitle_store import subtitle_store_node


@PipelineRegistry.register("subtitle_only")
def subtitle_only_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("subtitle_store", subtitle_store_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "subtitle")
    graph.add_edge("subtitle", "subtitle_store")
    graph.add_edge("subtitle_store", END)
    return graph.compile()
