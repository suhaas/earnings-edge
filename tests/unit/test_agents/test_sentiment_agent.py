"""Unit tests for the sentiment agent: hedging/certainty ratios + tone surprise from the Store.

`_finbert` is faked, so no model download and no torch inference — these run in milliseconds.

Reference: skills/finbert-tone-analysis, skills/hedging-certainty-features, skills/sentiment-surprise

DRIFT — skills/hedging-certainty-features says to compute ratios SEPARATELY for prepared remarks
vs Q&A ("Q&A hedging spikes are the signal"), but the code only computes them for Q&A
(`h_qa, c_qa = _ratios(qa)`). `test_ratios_are_only_computed_for_qa` pins the code's behaviour.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from langgraph.store.base import BaseStore

from agentic_app.agents import sentiment_agent
from agentic_app.orchestration.state import EarningsState


class _Item:
    """Stands in for a langgraph store item (has .value)."""

    def __init__(self, tone: float) -> None:
        self.value = {"tone": tone}


class _FakeStore:
    def __init__(self, tones: list[float] | None = None) -> None:
        self._items = [_Item(t) for t in (tones or [])]
        self.last_search: tuple[Any, Any] = ((), None)

    def search(self, ns: Any, limit: int | None = None) -> list[_Item]:
        self.last_search = (ns, limit)
        return self._items


@pytest.fixture
def fake_tone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic tone: +1.0 for text containing 'good', -1.0 for 'bad', else 0.0."""

    def _tone(text: str) -> float:
        if "good" in text:
            return 1.0
        if "bad" in text:
            return -1.0
        return 0.0

    monkeypatch.setattr(sentiment_agent, "_tone", _tone)


def _state(**kw: Any) -> EarningsState:
    base: dict[str, Any] = {"ticker": "NVDA", "transcript_prepared": "", "transcript_qa": ""}
    base.update(kw)
    return cast(EarningsState, base)


def _run(state: EarningsState, store: _FakeStore) -> dict[str, Any]:
    out = sentiment_agent.sentiment_node(state, {}, store=cast(BaseStore, store))
    return cast(dict[str, Any], out["sentiment"][0])


# --- _ratios: hedging / certainty per 1000 tokens ---------------------------


def test_ratios_are_per_1000_tokens() -> None:
    """1 hedge word in 4 tokens -> 250 per 1000."""
    hedge, certainty = sentiment_agent._ratios("we may see growth")
    assert hedge == pytest.approx(250.0)
    assert certainty == pytest.approx(0.0)


def test_ratios_count_certainty_words() -> None:
    hedge, certainty = sentiment_agent._ratios("we will definitely deliver")
    assert certainty == pytest.approx(500.0)  # will + definitely of 4 tokens
    assert hedge == pytest.approx(0.0)


def test_ratios_are_case_insensitive() -> None:
    assert sentiment_agent._ratios("MAY")[0] == sentiment_agent._ratios("may")[0]


def test_ratios_on_empty_text_do_not_divide_by_zero() -> None:
    assert sentiment_agent._ratios("") == (0.0, 0.0)


def test_multi_word_hedges_cannot_match_the_tokenizer() -> None:
    """KNOWN GAP: the tokenizer is r"[a-z']+", so multi-word phrases can never match.

    skills/hedging-certainty-features is Loughran-McDonald-inspired, and LM includes phrases like
    "subject to". This documents that single-token matching cannot see them.
    """
    assert "subject to" not in sentiment_agent.HEDGE  # a phrase would be unmatchable
    assert sentiment_agent._ratios("subject to change") == (0.0, 0.0)


# --- tone -------------------------------------------------------------------


def test_current_tone_is_an_even_blend_of_prepared_and_qa(fake_tone: None) -> None:
    out = _run(_state(transcript_prepared="good", transcript_qa="bad"), _FakeStore())
    assert out["tone_prepared"] == 1.0
    assert out["tone_qa"] == -1.0
    assert out["current_tone"] == 0.0  # 0.5*1 + 0.5*(-1)
    assert out["tone_delta_prepared_vs_qa"] == 2.0


def test_net_certainty_is_certainty_minus_hedge(fake_tone: None) -> None:
    out = _run(_state(transcript_qa="we will definitely may"), _FakeStore())
    assert out["net_certainty_qa"] == pytest.approx(
        out["certainty_ratio_qa"] - out["hedge_ratio_qa"]
    )


def test_ratios_are_only_computed_for_qa(fake_tone: None) -> None:
    """DRIFT GUARD: the skill asks for prepared-vs-Q&A ratios; the code only does Q&A.

    Hedge words in the prepared remarks are invisible to the signal.
    """
    out = _run(_state(transcript_prepared="may may may may", transcript_qa=""), _FakeStore())
    assert out["hedge_ratio_qa"] == 0.0  # prepared-remarks hedging is not measured


# --- sentiment surprise from the Store (ADR-0005 / ADR-0006) ----------------


def test_surprise_needs_at_least_two_prior_quarters(fake_tone: None) -> None:
    out = _run(_state(transcript_qa="good"), _FakeStore([0.1]))  # only 1 prior
    assert out["n_quarters"] == 1
    assert out["sentiment_surprise"] == 0.0
    assert out["trailing_mean"] == out["current_tone"]  # falls back to self


def test_surprise_is_current_tone_minus_trailing_mean(fake_tone: None) -> None:
    out = _run(_state(transcript_prepared="good", transcript_qa="good"), _FakeStore([0.0, 0.5]))
    assert out["n_quarters"] == 2
    assert out["trailing_mean"] == pytest.approx(0.25)
    assert out["current_tone"] == 1.0
    assert out["sentiment_surprise"] == pytest.approx(0.75)


def test_empty_store_zeroes_the_surprise_this_is_bug_B1(fake_tone: None) -> None:
    """CHARACTERIZATION of the ADR-0006 bug, in numbers.

    On the SQLite default the Store is an InMemoryStore, so history is always empty:
    n_quarters == 0 and sentiment_surprise == 0.0 on EVERY run. That zeroes the 0.20-weighted
    tone term of the synthesis signal and caps confidence.

    When ADR-0006's SqliteStore swap lands, this test should FAIL for a real local run and be
    rewritten. It exists so that change is visible rather than silent.
    """
    out = _run(_state(transcript_prepared="good", transcript_qa="good"), _FakeStore([]))
    assert out["n_quarters"] == 0
    assert out["sentiment_surprise"] == 0.0
    assert out["trailing_mean"] == out["current_tone"]


def test_store_is_searched_by_ticker_namespace_with_an_8_quarter_window(fake_tone: None) -> None:
    """The namespace must stay in sync with delivery_agent's store.put (ADR-0005)."""
    store = _FakeStore([])
    _run(_state(ticker="AAPL"), store)
    assert store.last_search == (("sentiment_history", "AAPL"), 8)


def test_node_returns_a_single_element_list(fake_tone: None) -> None:
    """`sentiment` has an operator.add reducer — the node appends exactly one entry."""
    out = sentiment_agent.sentiment_node(_state(), {}, store=cast(BaseStore, _FakeStore()))
    assert len(out["sentiment"]) == 1
