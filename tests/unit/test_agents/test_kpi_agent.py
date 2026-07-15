"""Unit tests for the KPI agent's surprise and guidance maths.

Characterization tests. `_extractor` (Claude) and `_consensus` (yfinance) are faked, so these are
hermetic — no API key, no network.

Reference: skills/kpi-extraction, skills/earnings-surprise-detection, skills/guidance-raise-detection,
skills/consensus-estimate-retrieval
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from agentic_app.agents import kpi_agent
from agentic_app.orchestration.state import EarningsKPIs, EarningsState


class _FakeExtractor:
    def __init__(self, kpis: EarningsKPIs) -> None:
        self._kpis = kpis
        self.last_messages: Any = None

    def invoke(self, messages: Any) -> EarningsKPIs:
        self.last_messages = messages
        return self._kpis


def _install(
    monkeypatch: pytest.MonkeyPatch,
    kpis: EarningsKPIs,
    consensus: dict[str, float | None] | None = None,
) -> _FakeExtractor:
    extractor = _FakeExtractor(kpis)
    monkeypatch.setattr(kpi_agent, "_extractor", lambda: extractor)
    monkeypatch.setattr(
        kpi_agent,
        "_consensus",
        lambda _ticker: consensus
        or {"consensus_eps": None, "consensus_revenue": None, "consensus_eps_next_q": None},
    )
    return extractor


def _state(**kw: Any) -> EarningsState:
    base: dict[str, Any] = {
        "ticker": "NVDA",
        "year": 2025,
        "quarter": 4,
        "press_release_text": "PR",
        "transcript_prepared": "TP",
    }
    base.update(kw)
    return cast(EarningsState, base)


# --- _pct: surprise maths ---------------------------------------------------


def test_pct_is_percent_of_absolute_consensus() -> None:
    assert kpi_agent._pct(11.0, 10.0) == pytest.approx(10.0)


def test_pct_uses_abs_consensus_so_a_negative_beat_is_positive() -> None:
    """Beating a -10 estimate with -5 is a POSITIVE surprise. abs() in the denominator is why."""
    assert kpi_agent._pct(-5.0, -10.0) == pytest.approx(50.0)


def test_pct_guards_zero_consensus() -> None:
    """Division-by-zero guard — skills/earnings-surprise-detection calls this out explicitly."""
    assert kpi_agent._pct(5.0, 0.0) is None


@pytest.mark.parametrize(("actual", "cons"), [(None, 10.0), (10.0, None), (None, None)])
def test_pct_returns_none_when_either_side_is_missing(actual: Any, cons: Any) -> None:
    assert kpi_agent._pct(actual, cons) is None


def test_pct_of_zero_actual_is_minus_100_not_none() -> None:
    """0.0 actual is a real datum, not a missing one."""
    assert kpi_agent._pct(0.0, 10.0) == pytest.approx(-100.0)


# --- guidance direction -----------------------------------------------------


@pytest.mark.parametrize(
    ("guide", "expected"),
    [
        (10.5, "raise"),  # +5%  > 1
        (9.5, "cut"),  # -5%  < -1
        (10.05, "maintain"),  # +0.5% inside the band
        (9.95, "maintain"),  # -0.5% inside the band
    ],
)
def test_guidance_direction_thresholds(
    monkeypatch: pytest.MonkeyPatch, guide: float, expected: str
) -> None:
    """>1% raise, <-1% cut, else maintain (skills/guidance-raise-detection)."""
    _install(
        monkeypatch,
        EarningsKPIs(eps_guidance_next_q=guide),
        {"consensus_eps": None, "consensus_revenue": None, "consensus_eps_next_q": 10.0},
    )
    out = kpi_agent.kpi_node(_state())
    assert out["kpis"][0]["guidance_direction"] == expected
    assert out["kpis"][0]["has_guidance_raise"] is (expected == "raise")


@pytest.mark.parametrize(
    "language", ["We are raising guidance", "increased outlook", "above prior"]
)
def test_guidance_language_fallback_when_no_numeric_guide(
    monkeypatch: pytest.MonkeyPatch, language: str
) -> None:
    """With no numeric guidance, fall back to keywords: 'rais', 'increas', 'above'."""
    _install(monkeypatch, EarningsKPIs(guidance_language=language))
    out = kpi_agent.kpi_node(_state())
    assert out["kpis"][0]["guidance_direction"] == "raise"


def test_guidance_defaults_to_none_when_nothing_is_known(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, EarningsKPIs())
    out = kpi_agent.kpi_node(_state())
    assert out["kpis"][0]["guidance_direction"] == "none"
    assert out["kpis"][0]["has_guidance_raise"] is False


def test_numeric_guidance_wins_over_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """The numeric branch is an `if`/`elif` — language must not override a numeric cut."""
    _install(
        monkeypatch,
        EarningsKPIs(eps_guidance_next_q=9.0, guidance_language="raising guidance"),
        {"consensus_eps": None, "consensus_revenue": None, "consensus_eps_next_q": 10.0},
    )
    out = kpi_agent.kpi_node(_state())
    assert out["kpis"][0]["guidance_direction"] == "cut"


# --- node contract ----------------------------------------------------------


def test_node_merges_kpis_consensus_and_derived_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        EarningsKPIs(eps_actual=11.0, revenue_actual=110.0),
        {"consensus_eps": 10.0, "consensus_revenue": 100.0, "consensus_eps_next_q": None},
    )
    out = kpi_agent.kpi_node(_state())
    k = out["kpis"][0]
    assert k["eps_actual"] == 11.0  # from EarningsKPIs
    assert k["consensus_eps"] == 10.0  # from _consensus
    assert k["eps_surprise_pct"] == pytest.approx(10.0)  # derived
    assert k["revenue_surprise_pct"] == pytest.approx(10.0)


def test_node_returns_a_single_element_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """`kpis` has an operator.add reducer — the node appends exactly one entry."""
    _install(monkeypatch, EarningsKPIs())
    assert len(kpi_agent.kpi_node(_state())["kpis"]) == 1


def test_extractor_failure_is_captured_as_an_error_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An LLM failure must not kill the graph — it lands in state['errors']."""

    class _Boom:
        def invoke(self, _messages: Any) -> Any:
            raise RuntimeError("rate limited")

    monkeypatch.setattr(kpi_agent, "_extractor", lambda: _Boom())
    out = kpi_agent.kpi_node(_state())
    assert out["kpis"] == [{}]
    assert len(out["errors"]) == 1
    assert "rate limited" in out["errors"][0]


def test_input_text_is_truncated_to_18000_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """A whole call must fit the context window — the cap is why RAG isn't needed (ADR-0007)."""
    extractor = _install(monkeypatch, EarningsKPIs())
    kpi_agent.kpi_node(_state(press_release_text="x" * 50_000))
    user = extractor.last_messages[1]
    assert len(user["content"]) == 18_000
