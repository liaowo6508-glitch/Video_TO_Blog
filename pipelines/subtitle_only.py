from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from engine.registry import PipelineRegistry
from engine.state import PipelineState
from nodes.ingest import ingest_node
from nodes.subtitle import subtitle_node
from nodes.subtitle_clean import subtitle_clean_node
from nodes.subtitle_store import subtitle_store_node


def route_after_subtitle(state: PipelineState) -> str:
    return "subtitle_clean" if state.get("has_subtitle") else "subtitle_store"


@PipelineRegistry.register("subtitle_only")
def subtitle_only_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("subtitle_clean", subtitle_clean_node)
    graph.add_node("subtitle_store", subtitle_store_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "subtitle")
    graph.add_conditional_edges(
        "subtitle",
        route_after_subtitle,
        {
            "subtitle_clean": "subtitle_clean",
            "subtitle_store": "subtitle_store",
        },
    )
    graph.add_edge("subtitle_clean", "subtitle_store")
    graph.add_edge("subtitle_store", END)
    return graph.compile()
