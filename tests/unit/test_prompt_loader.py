"""Tests for PromptLoader: registry resolution + {{shared.*}} include rendering.

Because the agents now pull their system prompts from here, these tests turn a broken
prompt (missing role, unresolved include, wrong section) into a hard failure.
"""

from __future__ import annotations

import pytest

from agentic_app.prompts.loader import PromptError, prompt_loader

ROLES = ["ingestion", "sentiment", "kpi", "synthesis", "evaluation", "delivery"]


@pytest.mark.parametrize("role", ROLES)
def test_every_role_renders(role: str) -> None:
    text = prompt_loader.load(role)
    assert text.strip(), f"empty prompt for {role}"
    # No include token may survive rendering.
    assert "{{shared" not in text, f"unrendered include left in {role} prompt:\n{text}"


@pytest.mark.parametrize("role", ROLES)
def test_shared_safety_is_inlined(role: str) -> None:
    # Every role's prompt opens with {{shared.safety}}; the rendered body must contain
    # a stable phrase from prompts/shared/safety.md.
    assert "insider trading" in prompt_loader.load(role)


def test_section_selector_extracts_only_that_section() -> None:
    # delivery/v1.md uses {{shared.output_formats.json}} -> the "JSON Output Contract"
    # section of shared/output_formats.md, and NOT the later "Error Response" section.
    text = prompt_loader.load("delivery")
    assert "JSON Output Contract" in text
    assert "Error Response" not in text


def test_kpi_prompt_keeps_extraction_example() -> None:
    # The few-shot example moved into the prompt file; losing it would silently degrade
    # extraction, so assert the operational content is present.
    assert "39300000000.0" in prompt_loader.load("kpi")


def test_unknown_role_raises() -> None:
    with pytest.raises(PromptError):
        prompt_loader.load("does-not-exist")
