"""Synthesis agent: fuse sentiment + KPIs into a SurpriseSignal and render a brief."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from langchain_anthropic import ChatAnthropic

from agentic_app.orchestration.state import EarningsState, SurpriseSignal
from agentic_app.prompts.loader import prompt_loader


@lru_cache(maxsize=1)
def _llm() -> Any:
    """Chat model, built lazily so importing this module needs no API key."""
    return ChatAnthropic(model="claude-sonnet-4-5", temperature=0.2)  # type: ignore[call-arg]


def _z(x: float | None, scale: float) -> float:
    return max(-3, min(3, (x or 0) / scale))


def synthesize_node(state: EarningsState) -> dict[str, Any]:
    s = (state.get("sentiment") or [{}])[-1]
    k = (state.get("kpis") or [{}])[-1]

    raw = (
        0.35 * _z(k.get("eps_surprise_pct"), 10)
        + 0.20 * _z(k.get("revenue_surprise_pct"), 8)
        + 0.20 * (s.get("sentiment_surprise") or 0) * 3
        + 0.10 * _z(s.get("net_certainty_qa"), 5)
        + 0.15 * (1 if k.get("has_guidance_raise") else 0)
    )
    score = 100 * math.tanh(raw)
    direction = "bullish" if score > 10 else "bearish" if score < -10 else "neutral"
    n_inputs = sum(
        v is not None
        for v in [
            k.get("eps_surprise_pct"),
            k.get("revenue_surprise_pct"),
            k.get("guidance_direction"),
        ]
    )
    confidence = min(1.0, 0.4 + 0.15 * n_inputs + 0.05 * s.get("n_quarters", 0))

    rationale = (
        f"EPS surprise {k.get('eps_surprise_pct')}%, revenue surprise "
        f"{k.get('revenue_surprise_pct')}%, tone surprise "
        f"{round(s.get('sentiment_surprise', 0), 3)}, guidance "
        f"{k.get('guidance_direction')}."
    )

    user_msg = f"""Write the analyst brief for {state["ticker"]} Q{state["quarter"]} FY{state["year"]}.
SIGNAL: score={round(score, 1)} ({direction}), confidence={round(confidence, 2)}.
KPIs: {k}
SENTIMENT: {s}"""
    brief = (
        _llm()
        .invoke(
            [
                {"role": "system", "content": prompt_loader.load("synthesis")},
                {"role": "user", "content": user_msg},
            ]
        )
        .content
    )

    sig = SurpriseSignal(
        score=round(score, 1),
        direction=direction,
        confidence=round(confidence, 2),
        rationale=rationale,
        brief_markdown=brief,
    )
    return {
        "signal": sig.model_dump(),
        "brief_markdown": brief,
        "revision_count": state.get("revision_count", 0),
    }


# from agentic_app.orchestration.state import EarningsState


# def synthesize_node(state: EarningsState) -> dict:
#     """Fuse features into a transparent signal + analyst brief.

#     Called both by the `synthesize` node and re-invoked by the `revise` node,
#     so it must be synchronous and idempotent on its inputs.

#     TODO: weighted signal scoring + brief rendering
#     (see skills/signal-synthesis-scoring, skills/analyst-brief-generation).
#     """
#     return {
#         "signal": {
#             "score": 0.0,
#             "direction": "neutral",
#             "confidence": 0.0,
#             "rationale": "stub",
#         },
#         "brief_markdown": "# Stub brief\n",
#     }
