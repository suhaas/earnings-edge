"""Evaluation agent: grounding/faithfulness check + self-correction routing."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from openevals.llm import create_llm_as_judge
from openevals.prompts import HALLUCINATION_PROMPT

from agentic_app.orchestration.state import EarningsState


@lru_cache(maxsize=1)
def _judge() -> Any:
    """LLM-as-judge, built lazily so importing this module needs no API key."""
    return create_llm_as_judge(
        prompt=HALLUCINATION_PROMPT,
        model="anthropic:claude-sonnet-4-5",
        feedback_key="faithfulness",
    )


def evaluate_node(state: EarningsState) -> dict[str, Any]:
    context = {
        "transcript": (state.get("transcript_prepared", "") + state.get("transcript_qa", ""))[
            :12000
        ],
        "kpis": (state.get("kpis") or [{}])[-1],
    }
    res = _judge()(
        inputs=str(context),
        outputs=state.get("brief_markdown", ""),
    )
    raw = res.get("score")
    score = 1.0 if raw is True else 0.0 if raw is False else float(raw)
    return {"grounding_score": score, "grounding_comment": res.get("comment", "")}


def route_after_eval(state: EarningsState) -> str:
    """Self-correction: loop back to synthesis if not grounded and under retry budget."""
    if state.get("grounding_score", 0.0) < 0.8 and state.get("revision_count", 0) < 2:
        return "revise"
    return "deliver"


# from agentic_app.orchestration.state import EarningsState

# # Revision budget: caps the evaluate -> revise -> evaluate self-correction loop.
# MAX_REVISIONS = 2
# GROUNDING_THRESHOLD = 0.7


# def evaluate_node(state: EarningsState) -> dict:
#     """Score how well the brief is grounded in the extracted KPIs/sentiment.

#     TODO: grounding-faithfulness eval (see skills/grounding-faithfulness-eval).
#     """
#     return {"grounding_score": 1.0, "grounding_comment": "stub"}


# def route_after_eval(state: EarningsState) -> str:
#     """Conditional edge: loop back to `revise` on low grounding, else `deliver`.

#     The revision budget prevents an infinite self-correction loop (see CLAUDE.md
#     "Agent Loops"). `revision_count` is bumped by the `revise` node in graph.py.
#     """
#     if (
#         state.get("grounding_score", 1.0) < GROUNDING_THRESHOLD
#         and state.get("revision_count", 0) < MAX_REVISIONS
#     ):
#         return "revise"
#     return "deliver"
