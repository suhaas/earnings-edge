"""Unit tests for the synthesis agent's scoring model.

These are CHARACTERIZATION tests: they pin down what `synthesize_node` computes today, so a
refactor that claims to be behaviour-neutral has something to prove it against. The weights are
restated as literals rather than imported, so changing a weight in production turns a test red
instead of passing silently.

Reference: skills/signal-synthesis-scoring/SKILL.md

DRIFT — the code does NOT match that skill on two transforms (weights DO match):
  skill:26  ... + 0.20*sentiment_surprise + 0.10*net_certainty_qa ...
  code:32   ... + 0.20 * sentiment_surprise * 3          <- undocumented 3x amplification
  code:33   ... + 0.10 * _z(net_certainty_qa, 5)         <- skill says raw, code z-scales
`test_sentiment_surprise_is_amplified_3x` and `test_net_certainty_is_z_scaled` pin the CODE's
behaviour. Do not "fix" them to match the skill without deciding which is authoritative.

Hermetic: `_llm` is faked, so no API key and no network. `prompt_loader.load("synthesis")` still
runs — it only touches the filesystem.
"""

from __future__ import annotations

import math
from typing import Any, cast

import pytest

from agentic_app.agents import synthesis_agent
from agentic_app.orchestration.state import EarningsState


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    """Stands in for ChatAnthropic. Records the prompt so we can assert on it."""

    def __init__(self) -> None:
        self.last_messages: Any = None

    def invoke(self, messages: Any) -> _FakeMessage:
        self.last_messages = messages
        return _FakeMessage("# Brief\n")


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> _FakeLLM:
    llm = _FakeLLM()
    monkeypatch.setattr(synthesis_agent, "_llm", lambda: llm)
    return llm


def _state(**kw: Any) -> EarningsState:
    """Build an EarningsState. Cast rather than `# type: ignore`, so these tests type-check
    whether or not mypy can resolve the package (the pre-commit hook currently cannot)."""
    base: dict[str, Any] = {
        "ticker": "NVDA",
        "year": 2025,
        "quarter": 4,
        "sentiment": [{}],
        "kpis": [{}],
    }
    base.update(kw)
    return cast(EarningsState, base)


# --- _z ---------------------------------------------------------------------


def test_z_scales_by_the_given_divisor() -> None:
    assert synthesis_agent._z(15.0, 10) == 1.5


def test_z_clamps_to_plus_minus_three() -> None:
    assert synthesis_agent._z(1_000.0, 10) == 3
    assert synthesis_agent._z(-1_000.0, 10) == -3


def test_z_treats_none_as_zero() -> None:
    assert synthesis_agent._z(None, 10) == 0


def test_z_treats_zero_as_zero_not_none() -> None:
    """0.0 is falsy — `x or 0` must not turn a real 0.0 into a different value."""
    assert synthesis_agent._z(0.0, 10) == 0


# --- the scoring model ------------------------------------------------------


def test_all_inputs_absent_scores_zero_neutral_with_floor_confidence(fake_llm: _FakeLLM) -> None:
    out = synthesis_agent.synthesize_node(_state())
    sig = out["signal"]
    assert sig["score"] == 0.0
    assert sig["direction"] == "neutral"
    assert sig["confidence"] == 0.4  # 0.4 + 0.15*0 + 0.05*0


def test_score_is_100_tanh_of_the_weighted_sum(fake_llm: _FakeLLM) -> None:
    """Golden: a max-positive EPS surprise alone. Weights restated literally on purpose."""
    out = synthesis_agent.synthesize_node(_state(kpis=[{"eps_surprise_pct": 100.0}]))
    expected_raw = 0.35 * 3  # _z(100, 10) clamps to 3
    assert out["signal"]["score"] == round(100 * math.tanh(expected_raw), 1)


def test_every_weighted_term_contributes(fake_llm: _FakeLLM) -> None:
    """All five terms at once — catches a dropped or reordered term."""
    out = synthesis_agent.synthesize_node(
        _state(
            kpis=[
                {
                    "eps_surprise_pct": 10.0,  # _z(10, 10) -> 1.0
                    "revenue_surprise_pct": 8.0,  # _z(8, 8)  -> 1.0
                    "has_guidance_raise": True,  # -> 1
                    "guidance_direction": "raise",
                }
            ],
            sentiment=[{"sentiment_surprise": 0.1, "net_certainty_qa": 5.0}],  # _z(5, 5) -> 1.0
        )
    )
    expected_raw = (
        0.35 * 1.0  # eps
        + 0.20 * 1.0  # revenue
        + 0.20 * 0.1 * 3  # sentiment surprise, amplified 3x (see module docstring)
        + 0.10 * 1.0  # net certainty, z-scaled
        + 0.15 * 1  # guidance raise
    )
    assert out["signal"]["score"] == round(100 * math.tanh(expected_raw), 1)


def test_sentiment_surprise_is_amplified_3x(fake_llm: _FakeLLM) -> None:
    """DRIFT GUARD: the code multiplies sentiment_surprise by 3; the skill does not.

    If this fails, someone changed the amplification. Decide deliberately whether the code or
    skills/signal-synthesis-scoring/SKILL.md:26 is authoritative — do not just re-fit the test.
    """
    out = synthesis_agent.synthesize_node(_state(sentiment=[{"sentiment_surprise": 0.5}]))
    amplified = round(100 * math.tanh(0.20 * 0.5 * 3), 1)
    unamplified = round(100 * math.tanh(0.20 * 0.5), 1)
    assert out["signal"]["score"] == amplified
    assert out["signal"]["score"] != unamplified


def test_net_certainty_is_z_scaled(fake_llm: _FakeLLM) -> None:
    """DRIFT GUARD: the code z-scales net_certainty_qa by 5; the skill uses it raw."""
    out = synthesis_agent.synthesize_node(
        _state(sentiment=[{"net_certainty_qa": 100.0}])  # raw would dominate; _z clamps to 3
    )
    assert out["signal"]["score"] == round(100 * math.tanh(0.10 * 3), 1)


# --- direction --------------------------------------------------------------


@pytest.mark.parametrize(
    ("eps_surprise", "expected"),
    [
        (100.0, "bullish"),  # score ~ +78
        (-100.0, "bearish"),  # score ~ -78
        (0.0, "neutral"),
    ],
)
def test_direction_thresholds(fake_llm: _FakeLLM, eps_surprise: float, expected: str) -> None:
    out = synthesis_agent.synthesize_node(_state(kpis=[{"eps_surprise_pct": eps_surprise}]))
    assert out["signal"]["direction"] == expected


def test_direction_is_neutral_inside_the_plus_minus_10_band(fake_llm: _FakeLLM) -> None:
    """A small positive score must still read neutral — the band is +/-10, not sign()."""
    out = synthesis_agent.synthesize_node(
        _state(kpis=[{"eps_surprise_pct": 1.0}])  # -> score ~ +3.5
    )
    assert 0 < out["signal"]["score"] < 10
    assert out["signal"]["direction"] == "neutral"


# --- confidence -------------------------------------------------------------


def test_confidence_counts_non_none_inputs_and_quarters(fake_llm: _FakeLLM) -> None:
    out = synthesis_agent.synthesize_node(
        _state(
            kpis=[
                {
                    "eps_surprise_pct": 1.0,
                    "revenue_surprise_pct": 1.0,
                    "guidance_direction": "maintain",
                }
            ],
            sentiment=[{"n_quarters": 2}],
        )
    )
    # 0.4 + 0.15*3 inputs + 0.05*2 quarters = 0.95
    assert out["signal"]["confidence"] == 0.95


def test_confidence_is_capped_at_one(fake_llm: _FakeLLM) -> None:
    out = synthesis_agent.synthesize_node(
        _state(
            kpis=[
                {
                    "eps_surprise_pct": 1.0,
                    "revenue_surprise_pct": 1.0,
                    "guidance_direction": "raise",
                }
            ],
            sentiment=[{"n_quarters": 99}],
        )
    )
    assert out["signal"]["confidence"] == 1.0


def test_zero_quarters_penalises_confidence(fake_llm: _FakeLLM) -> None:
    """The ADR-0006 bug in numbers: no sentiment history caps confidence at 0.85, not 0.95."""
    out = synthesis_agent.synthesize_node(
        _state(
            kpis=[
                {
                    "eps_surprise_pct": 1.0,
                    "revenue_surprise_pct": 1.0,
                    "guidance_direction": "maintain",
                }
            ],
            sentiment=[{"n_quarters": 0}],
        )
    )
    assert out["signal"]["confidence"] == 0.85


# --- state contract ---------------------------------------------------------


def test_reads_only_the_last_sentiment_and_kpi_entry(fake_llm: _FakeLLM) -> None:
    """Both are operator.add lists; synthesis must use [-1], not merge."""
    out = synthesis_agent.synthesize_node(
        _state(
            kpis=[{"eps_surprise_pct": -100.0}, {"eps_surprise_pct": 100.0}],
            sentiment=[{"sentiment_surprise": -9.0}, {}],
        )
    )
    assert out["signal"]["direction"] == "bullish"  # driven by the LAST kpi entry


def test_revision_count_passes_through_untouched(fake_llm: _FakeLLM) -> None:
    """graph.py's `revise` wrapper owns the increment; the node must not bump it."""
    out = synthesis_agent.synthesize_node(_state(revision_count=1))
    assert out["revision_count"] == 1


def test_brief_is_returned_both_top_level_and_in_the_signal(fake_llm: _FakeLLM) -> None:
    out = synthesis_agent.synthesize_node(_state())
    assert out["brief_markdown"] == "# Brief\n"
    assert out["signal"]["brief_markdown"] == "# Brief\n"


def test_prompt_is_the_synthesis_role_and_carries_the_signal(fake_llm: _FakeLLM) -> None:
    synthesis_agent.synthesize_node(_state(kpis=[{"eps_surprise_pct": 100.0}]))
    system, user = fake_llm.last_messages
    assert system["role"] == "system"
    assert system["content"].strip()  # rendered from prompts/synthesis/v1.md
    assert "NVDA Q4 FY2025" in user["content"]
    assert "bullish" in user["content"]
