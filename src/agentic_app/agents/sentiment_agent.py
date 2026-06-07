"""Sentiment agent: FinBERT tone + hedging/certainty features over the transcript."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from transformers import pipeline

from agentic_app.orchestration.state import EarningsState

HEDGE = {
    "may",
    "might",
    "could",
    "possibly",
    "approximately",
    "uncertain",
    "believe",
    "expect",
    "hope",
    "appears",
    "likely",
    "potential",
    "depends",
}
CERTAINTY = {
    "will",
    "definitely",
    "clearly",
    "confident",
    "strong",
    "record",
    "certainly",
    "committed",
    "guarantee",
    "robust",
    "exceeded",
}


@lru_cache(maxsize=1)
def _finbert() -> Any:
    return pipeline(
        "text-classification", model="ProsusAI/finbert", truncation=True, max_length=512, top_k=None
    )


def _tone(text: str) -> float:
    if not text.strip():
        return 0.0
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()][:200]
    nlp = _finbert()
    scores = []
    for out in nlp(sents):
        d = {o["label"].lower(): o["score"] for o in out}
        scores.append(d.get("positive", 0) - d.get("negative", 0))
    return sum(scores) / len(scores) if scores else 0.0


def _ratios(text: str) -> tuple[float, float]:
    toks = re.findall(r"[a-z']+", text.lower())
    n = max(len(toks), 1)
    h = sum(t in HEDGE for t in toks) / n * 1000
    c = sum(t in CERTAINTY for t in toks) / n * 1000
    return h, c


def sentiment_node(
    state: EarningsState, config: RunnableConfig, *, store: BaseStore
) -> dict[str, Any]:
    prep, qa = state.get("transcript_prepared", ""), state.get("transcript_qa", "")
    tone_prep, tone_qa = _tone(prep), _tone(qa)
    h_qa, c_qa = _ratios(qa)
    current_tone = 0.5 * tone_prep + 0.5 * tone_qa

    # ---- sentiment-surprise from cross-thread Store memory ----
    ticker = state["ticker"]
    ns = ("sentiment_history", ticker)
    prior = store.search(ns, limit=8)
    tones = [it.value["tone"] for it in prior] if prior else []
    trailing_mean = sum(tones) / len(tones) if len(tones) >= 2 else current_tone
    sentiment_surprise = current_tone - trailing_mean if len(tones) >= 2 else 0.0

    return {
        "sentiment": [
            {
                "tone_prepared": tone_prep,
                "tone_qa": tone_qa,
                "tone_delta_prepared_vs_qa": tone_prep - tone_qa,
                "hedge_ratio_qa": h_qa,
                "certainty_ratio_qa": c_qa,
                "net_certainty_qa": c_qa - h_qa,
                "current_tone": current_tone,
                "trailing_mean": trailing_mean,
                "n_quarters": len(tones),
                "sentiment_surprise": sentiment_surprise,
            }
        ]
    }


# from agentic_app.orchestration.state import EarningsState


# def sentiment_node(state: EarningsState) -> dict:
#     """Compute tone/sentiment features. Returns a list (reducer appends).

#     TODO: FinBERT tone analysis + hedging-certainty features
#     (see skills/finbert-tone-analysis, skills/hedging-certainty-features).
#     TODO: add a `store: BaseStore` parameter to receive the injected Store.
#     """
#     return {"sentiment": []}
