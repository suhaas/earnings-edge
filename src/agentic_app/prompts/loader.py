"""Prompt loading and rendering."""

from __future__ import annotations


class PromptLoader:
    """Load and render versioned prompts."""

    def load(self, role: str) -> str:
        """Load the active prompt for a role."""
        return f"Prompt for {role}"


prompt_loader = PromptLoader()
