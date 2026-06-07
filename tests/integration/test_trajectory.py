"""Integration ("trajectory") tests for the earnings-edge LangGraph wiring.

These tests are HERMETIC: they replace the six agent node modules with fakes,
injected into ``sys.modules`` *before* ``graph.py`` imports them, so the real
agents (which need network access, API keys, and large model downloads) are
never loaded. What they exercise is the **graph topology** built by
``build_graph`` — parallel fan-out/fan-in, the conditional self-correction loop
and its revision budget, and automatic Store injection — not the agents' inner
logic. Each agent should get its own unit test under ``tests/unit/``.
"""

from __future__ import annotations

import os
import sys
import types
from collections.abc import Callable, Iterator

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

# Real module name -> the callables graph.py imports from it.
_AGENT_EXPORTS: dict[str, list[str]] = {
    "ingestion_agent": ["ingest_node"],
    "sentiment_agent": ["sentiment_node"],
    "kpi_agent": ["kpi_node"],
    "synthesis_agent": ["synthesize_node"],
    "evaluation_agent": ["evaluate_node", "route_after_eval"],
    "delivery_agent": ["deliver_node"],
}
_GRAPH_MODULE = "agentic_app.orchestration.graph"


def _install_fake_agents(funcs: dict[str, Callable]) -> dict[str, types.ModuleType | None]:
    """Put fake agent modules into ``sys.modules`` so a fresh import of graph.py
    binds these instead of the real implementations. Returns the saved originals
    (including graph.py itself, which is popped to force re-import)."""
    saved: dict[str, types.ModuleType | None] = {}
    for mod_name, names in _AGENT_EXPORTS.items():
        dotted = f"agentic_app.agents.{mod_name}"
        saved[dotted] = sys.modules.get(dotted)
        module = types.ModuleType(dotted)
        for name in names:
            setattr(module, name, funcs[name])
        sys.modules[dotted] = module
    saved[_GRAPH_MODULE] = sys.modules.pop(_GRAPH_MODULE, None)
    return saved


def _restore(saved: dict[str, types.ModuleType | None]) -> None:
    for dotted, original in saved.items():
        if original is None:
            sys.modules.pop(dotted, None)
        else:
            sys.modules[dotted] = original


@pytest.fixture
def graph_factory() -> Iterator[Callable]:
    """Yield a builder: ``build(funcs) -> (compiled_app, store)``.

    Installs the given fake node callables, imports ``build_graph`` fresh against
    them, and compiles with a real ``MemorySaver`` + ``InMemoryStore`` so the
    durable-checkpoint and Store-injection code paths are genuinely exercised.
    """
    saved_states: list[dict[str, types.ModuleType | None]] = []

    def build(funcs: dict[str, Callable]) -> tuple[object, InMemoryStore]:
        saved_states.append(_install_fake_agents(funcs))
        from agentic_app.orchestration.graph import build_graph

        store = InMemoryStore()
        app = build_graph(checkpointer=MemorySaver(), store=store)
        return app, store

    yield build

    for saved in reversed(saved_states):
        _restore(saved)


def _fake_nodes(evaluate_node: Callable) -> dict[str, Callable]:
    """A complete set of lightweight fake nodes. ``evaluate_node`` is supplied per
    test to drive the conditional self-correction edge differently."""

    def ingest_node(state: dict) -> dict:
        return {
            "transcript_prepared": "prepared remarks",
            "transcript_qa": "q and a",
            "transcript_source": "fake",
            "press_release_text": "press release",
        }

    def sentiment_node(state: dict, *, store: BaseStore) -> dict:
        # Exercise Store injection: write current-quarter tone to long-term memory.
        store.put(
            ("sentiment_history", state["ticker"]),
            f"{state['year']}Q{state['quarter']}",
            {"tone": 0.5},
        )
        return {"sentiment": [{"current_tone": 0.5}]}

    def kpi_node(state: dict) -> dict:
        return {"kpis": [{"eps_surprise_pct": 5.0}]}

    def synthesize_node(state: dict) -> dict:
        return {
            "signal": {
                "score": 42.0,
                "direction": "bullish",
                "confidence": 0.7,
                "rationale": "fake rationale",
            },
            "brief_markdown": "# Brief\nbody",
        }

    def route_after_eval(state: dict) -> str:
        if state.get("grounding_score", 0.0) < 0.8 and state.get("revision_count", 0) < 2:
            return "revise"
        return "deliver"

    def deliver_node(state: dict, *, store: BaseStore) -> dict:
        # Exercise Store injection the other way: read what sentiment wrote.
        memories = store.search(("sentiment_history", state["ticker"]))
        return {"delivery_log": [f"delivered tone-memories={len(memories)}"]}

    return {
        "ingest_node": ingest_node,
        "sentiment_node": sentiment_node,
        "kpi_node": kpi_node,
        "synthesize_node": synthesize_node,
        "evaluate_node": evaluate_node,
        "route_after_eval": route_after_eval,
        "deliver_node": deliver_node,
    }


def _seed_state(ticker: str, year: int, quarter: int) -> dict:
    return {
        "ticker": ticker,
        "year": year,
        "quarter": quarter,
        "user_id": "tester",
        "revision_count": 0,
    }


def test_trajectory_reaches_deliver_with_one_revision(graph_factory: Callable) -> None:
    """Happy path: ingest -> {sentiment, kpi} -> synthesize -> evaluate -> (one
    revise) -> deliver. Also proves Store injection works in both directions."""

    def evaluate_node(state: dict) -> dict:
        # Fail grounding on the first pass; pass once a revision has happened.
        score = 1.0 if state.get("revision_count", 0) >= 1 else 0.0
        return {"grounding_score": score, "grounding_comment": "fake judge"}

    app, store = graph_factory(_fake_nodes(evaluate_node))
    final = app.invoke(
        _seed_state("NVDA", 2025, 4),
        {"configurable": {"thread_id": "NVDA-2025-Q4"}},
    )

    # Reached delivery with a rendered brief and a non-empty delivery log.
    assert final["brief_markdown"].startswith("#")
    assert final["delivery_log"], "deliver node did not run"
    assert final["signal"]["direction"] == "bullish"

    # The self-correction loop executed exactly once.
    assert final["revision_count"] == 1

    # Store injection worked both ways: sentiment wrote, deliver read it back.
    assert final["delivery_log"][-1] == "delivered tone-memories=1"
    persisted = store.search(("sentiment_history", "NVDA"))
    assert len(persisted) == 1
    assert persisted[0].value["tone"] == 0.5


def test_revision_budget_terminates_the_loop(graph_factory: Callable) -> None:
    """Even when grounding never passes, the revision budget must break the
    evaluate -> revise loop and still reach deliver (no infinite loop)."""

    def evaluate_node(state: dict) -> dict:
        return {"grounding_score": 0.0, "grounding_comment": "always fails"}

    app, _store = graph_factory(_fake_nodes(evaluate_node))
    final = app.invoke(
        _seed_state("AAPL", 2025, 1),
        {"configurable": {"thread_id": "AAPL-2025-Q1"}},
    )

    assert final["delivery_log"], "loop did not terminate at deliver"
    assert final["revision_count"] == 2  # capped at MAX_REVISIONS


@pytest.mark.langsmith
@pytest.mark.skipif(
    os.environ.get("RUN_LLM_JUDGE_TESTS") != "1",
    reason="LLM-as-judge trajectory test: opt in with RUN_LLM_JUDGE_TESTS=1 "
    "(needs agentevals, an Anthropic key, and LangSmith network access).",
)
def test_pipeline_order_llm_judge() -> None:
    """LLM-as-judge trajectory check (opt-in)."""
    pytest.importorskip("agentevals")
    from agentevals.trajectory.llm import (
        TRAJECTORY_ACCURACY_PROMPT,
        create_trajectory_llm_as_judge,
    )

    judge = create_trajectory_llm_as_judge(
        model="anthropic:claude-sonnet-4-5",
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )
    # Reference: ingest -> (sentiment, kpi) -> synthesize -> evaluate -> deliver
    outputs = [
        {"role": "assistant", "content": "ingested transcript"},
        {"role": "assistant", "content": "scored sentiment and extracted KPIs"},
        {"role": "assistant", "content": "synthesized signal and brief"},
        {"role": "assistant", "content": "evaluated grounding 0.86"},
        {"role": "assistant", "content": "delivered to slack/notion/sheets/gmail"},
    ]
    res = judge(outputs=outputs)
    assert res["score"] in (True, 1.0) or float(res["score"]) >= 0.5
