"""Unit tests for the evaluation agent: grounding score coercion + self-correction routing.

`route_after_eval` is the graph's only conditional edge, so these thresholds decide whether a run
loops or delivers. They are currently inline magic numbers (0.8 / 2).

Reference: skills/grounding-faithfulness-eval ("Threshold 0.8 with max 2 revisions")

NOTE: evaluation_agent.py:56-57 contains a COMMENTED-OUT block declaring
    # MAX_REVISIONS = 2
    # GROUNDING_THRESHOLD = 0.7
The commented threshold (0.7) DISAGREES with the live code (0.8), and its default for a missing
score is 1.0 (fail-open) where the live code uses 0.0 (fail-closed). These tests pin the LIVE
behaviour. Do not resurrect constants from that comment.
"""

from __future__ import annotations

from typing import Any

import pytest

from agentic_app.agents import evaluation_agent


class _FakeJudge:
    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result
        self.last_kwargs: dict[str, Any] = {}

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = kwargs
        return self._result


def _state(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ticker": "NVDA",
        "year": 2025,
        "quarter": 4,
        "transcript_prepared": "prepared",
        "transcript_qa": "qa",
        "kpis": [{"eps_actual": 1.0}],
        "brief_markdown": "# Brief",
    }
    base.update(kw)
    return base


# --- route_after_eval: the graph's only conditional edge --------------------


@pytest.mark.parametrize(
    ("score", "revisions", "expected"),
    [
        (0.9, 0, "deliver"),  # grounded -> deliver
        (0.8, 0, "deliver"),  # exactly at threshold -> NOT < 0.8 -> deliver
        (0.79, 0, "revise"),  # below threshold, budget available
        (0.0, 0, "revise"),
        (0.0, 1, "revise"),  # 1 < 2 -> still under budget
        (0.0, 2, "deliver"),  # budget exhausted -> deliver anyway
        (0.0, 99, "deliver"),
        (0.9, 2, "deliver"),
    ],
)
def test_routing_matrix(score: float, revisions: int, expected: str) -> None:
    state = {"grounding_score": score, "revision_count": revisions}
    assert evaluation_agent.route_after_eval(state) == expected  # type: ignore[arg-type]


def test_threshold_is_0_8_not_0_7() -> None:
    """DRIFT GUARD: the commented-out block at evaluation_agent.py:57 says 0.7. Live code is 0.8.

    0.75 must revise. If this fails, someone adopted the commented constant.
    """
    assert evaluation_agent.route_after_eval(  # type: ignore[arg-type]
        {"grounding_score": 0.75, "revision_count": 0}
    ) == "revise"


def test_missing_score_fails_closed_and_revises() -> None:
    """DRIFT GUARD: live default is 0.0 (revise). The commented block defaults to 1.0 (deliver).

    Opposite behaviour on a missing key — do not swap these.
    """
    assert evaluation_agent.route_after_eval({}) == "revise"  # type: ignore[arg-type]


def test_missing_revision_count_is_treated_as_zero() -> None:
    assert evaluation_agent.route_after_eval(  # type: ignore[arg-type]
        {"grounding_score": 0.0}
    ) == "revise"


# --- evaluate_node: score coercion -----------------------------------------


def test_boolean_true_score_becomes_1() -> None:
    """openevals returns bool or float depending on the judge — both must coerce."""
    judge = _FakeJudge({"score": True, "comment": "grounded"})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(evaluation_agent, "_judge", lambda: judge)
        out = evaluation_agent.evaluate_node(_state())  # type: ignore[arg-type]
    assert out["grounding_score"] == 1.0
    assert out["grounding_comment"] == "grounded"


def test_boolean_false_score_becomes_0() -> None:
    judge = _FakeJudge({"score": False, "comment": "hallucinated"})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(evaluation_agent, "_judge", lambda: judge)
        out = evaluation_agent.evaluate_node(_state())  # type: ignore[arg-type]
    assert out["grounding_score"] == 0.0


def test_float_score_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = _FakeJudge({"score": 0.42, "comment": ""})
    monkeypatch.setattr(evaluation_agent, "_judge", lambda: judge)
    out = evaluation_agent.evaluate_node(_state())  # type: ignore[arg-type]
    assert out["grounding_score"] == pytest.approx(0.42)


def test_missing_comment_defaults_to_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = _FakeJudge({"score": 1.0})
    monkeypatch.setattr(evaluation_agent, "_judge", lambda: judge)
    out = evaluation_agent.evaluate_node(_state())  # type: ignore[arg-type]
    assert out["grounding_comment"] == ""


# --- evaluate_node: judge contract -----------------------------------------


def test_judge_is_given_the_brief_as_output_and_transcript_as_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    judge = _FakeJudge({"score": 1.0, "comment": ""})
    monkeypatch.setattr(evaluation_agent, "_judge", lambda: judge)
    evaluation_agent.evaluate_node(_state())  # type: ignore[arg-type]

    assert judge.last_kwargs["outputs"] == "# Brief"
    assert "prepared" in judge.last_kwargs["context"]
    assert "NVDA Q4 FY2025" in judge.last_kwargs["inputs"]
    # No gold reference brief exists, so reference_outputs is deliberately empty.
    assert judge.last_kwargs["reference_outputs"] == ""


def test_context_transcript_is_truncated_to_12000_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = _FakeJudge({"score": 1.0, "comment": ""})
    monkeypatch.setattr(evaluation_agent, "_judge", lambda: judge)
    evaluation_agent.evaluate_node(  # type: ignore[arg-type]
        _state(transcript_prepared="x" * 20_000, transcript_qa="y" * 20_000)
    )
    # The transcript value inside the context dict is capped at 12k.
    assert "x" * 12_000 in judge.last_kwargs["context"]
    assert "x" * 12_001 not in judge.last_kwargs["context"]


def test_only_the_last_kpi_entry_is_used_as_ground_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = _FakeJudge({"score": 1.0, "comment": ""})
    monkeypatch.setattr(evaluation_agent, "_judge", lambda: judge)
    evaluation_agent.evaluate_node(  # type: ignore[arg-type]
        _state(kpis=[{"eps_actual": 1.0}, {"eps_actual": 999.0}])
    )
    assert "999.0" in judge.last_kwargs["context"]
