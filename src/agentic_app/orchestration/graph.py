r"""LangGraph wiring for the earnings-edge multi-agent pipeline.

Topology:
    ingest --> {sentiment, kpi}  (parallel fan-out)
    {sentiment, kpi} --> synthesize  (fan-in: waits for BOTH)
    synthesize --> evaluate
    evaluate --(route_after_eval)--> revise --> evaluate   (self-correction loop)
                                  \-> deliver --> END

Run it via the CLI: `python -m agentic_app.main run --ticker NVDA --year 2025 --quarter 4`.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from agentic_app.agents.delivery_agent import deliver_node
from agentic_app.agents.evaluation_agent import evaluate_node, route_after_eval
from agentic_app.agents.ingestion_agent import ingest_node
from agentic_app.agents.kpi_agent import kpi_node
from agentic_app.agents.sentiment_agent import sentiment_node
from agentic_app.agents.synthesis_agent import synthesize_node
from agentic_app.orchestration.state import EarningsState


def build_graph(checkpointer: Any | None = None, store: Any | None = None) -> Any:
    """Build and compile the earnings-edge StateGraph.

    Args:
        checkpointer: LangGraph checkpointer (e.g. SqliteSaver / PostgresSaver) for
            durable, resumable runs. None compiles an in-memory, non-durable graph.
        store: LangGraph BaseStore (e.g. InMemoryStore / PostgresStore) for
            cross-thread memory injected into nodes that declare a `store` param.
    """
    g = StateGraph(EarningsState)
    g.add_node("ingest", ingest_node)
    g.add_node("sentiment", sentiment_node)  # reads Store (injected automatically)
    g.add_node("kpi", kpi_node)
    g.add_node("synthesize", synthesize_node)

    def _bump_and_synth(state: EarningsState) -> dict[str, Any]:  # revision counter for the loop
        out = synthesize_node(state)
        out["revision_count"] = state.get("revision_count", 0) + (
            1 if state.get("brief_markdown") else 0
        )
        return out

    g.add_node("revise", _bump_and_synth)

    g.add_node("evaluate", evaluate_node)
    g.add_node("deliver", deliver_node)  # reads+writes Store

    g.set_entry_point("ingest")
    # ---- parallel fan-out: ingest -> {sentiment, kpi} ----
    g.add_edge("ingest", "sentiment")
    g.add_edge("ingest", "kpi")
    # ---- fan-in: synthesize waits for BOTH ----
    g.add_edge("sentiment", "synthesize")
    g.add_edge("kpi", "synthesize")
    g.add_edge("synthesize", "evaluate")
    g.add_edge("revise", "evaluate")
    # ---- conditional self-correction edge ----
    g.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {"revise": "revise", "deliver": "deliver"},
    )
    g.add_edge("deliver", END)

    return g.compile(checkpointer=checkpointer, store=store)
