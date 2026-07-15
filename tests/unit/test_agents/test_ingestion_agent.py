"""Unit tests for the ingestion agent's transcript segmentation.

Only the pure regex splitter is covered here. `ingest_node` itself is almost entirely external I/O
(earningscall + SEC EDGAR) and needs an integration test with recorded fixtures, not a unit test.

Reference: skills/transcript-ingestion-segmentation, skills/sec-edgar-8k-retrieval
"""

from __future__ import annotations

import pytest

from agentic_app.agents import ingestion_agent


@pytest.mark.parametrize(
    "boundary",
    [
        "Question-and-Answer Session",
        "question and answer",
        "We'll now begin the question portion",
        "We'll now take the first question",
        "Operator: Our first question comes from",
        "[Q&A]",
        "Q & A",
    ],
)
def test_recognised_qa_boundaries_split_the_transcript(boundary: str) -> None:
    prepared, qa = ingestion_agent._regex_split(f"Prepared remarks here. {boundary} Then answers.")
    assert prepared == "Prepared remarks here."
    assert qa.startswith(boundary[:5])


def test_uncontracted_we_will_now_take_is_not_recognised() -> None:
    """KNOWN GAP: the pattern is `we['’]?ll now (begin|take)` — it matches the CONTRACTION only.

    "We will now take your first question" has no contraction, no "question and answer" phrase, and
    no "operator", so nothing matches and the whole transcript lands in prepared remarks with an
    EMPTY `transcript_qa`. That silently zeroes `hedge_ratio_qa` / `certainty_ratio_qa` — which
    skills/hedging-certainty-features calls "the signal" — and halves the tone blend, since
    `current_tone = 0.5*tone_prepared + 0.5*tone_qa` with `tone_qa == 0.0`.

    This test documents the gap rather than asserting it is correct. Widening the alternation to
    `we (?:['’]?ll|will) now (?:begin|take)` would close it, but that changes segmentation for real
    transcripts and belongs in its own change with fixtures.
    """
    prepared, qa = ingestion_agent._regex_split(
        "Prepared remarks here. We will now take your first question. Then answers."
    )
    assert qa == ""
    assert prepared.endswith("Then answers.")  # everything, including the Q&A, is in prepared


def test_split_is_case_insensitive() -> None:
    _, qa = ingestion_agent._regex_split("Remarks. QUESTION-AND-ANSWER SESSION. Answers.")
    assert qa != ""


def test_no_boundary_puts_everything_in_prepared() -> None:
    """A transcript with no Q&A marker must not silently lose text."""
    prepared, qa = ingestion_agent._regex_split("Just prepared remarks, no Q and A marker here.")
    assert prepared == "Just prepared remarks, no Q and A marker here."
    assert qa == ""


def test_split_is_lossless_apart_from_whitespace() -> None:
    """Every character must land in exactly one side — no text may be dropped at the boundary."""
    text = "Alpha remarks. Question-and-Answer Session. Beta answers."
    prepared, qa = ingestion_agent._regex_split(text)
    assert (prepared + " " + qa).split() == text.split()


def test_empty_text_returns_empty_halves() -> None:
    assert ingestion_agent._regex_split("") == ("", "")


def test_boundary_at_the_very_start_yields_empty_prepared() -> None:
    prepared, qa = ingestion_agent._regex_split("[Q&A] all answers")
    assert prepared == ""
    assert qa == "[Q&A] all answers"


def test_only_the_first_boundary_splits() -> None:
    """Later mentions of 'question' inside the Q&A must not re-split."""
    prepared, qa = ingestion_agent._regex_split(
        "Remarks. Question-and-Answer Session. Next question please. More."
    )
    assert prepared == "Remarks."
    assert "Next question please." in qa
