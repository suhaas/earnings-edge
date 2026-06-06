"""Model registry: logical name → pinned model ID + role routing."""

from __future__ import annotations


class ModelRegistry:
    """Central registry for model selection by role."""

    models = {
        "cheap": "claude-3-5-haiku-20241022",
        "balanced": "claude-3-5-sonnet-20241022",
        "deep": "claude-3-opus-20250219",
    }

    def get(self, model_name: str) -> str:
        """Get model ID by logical name."""
        return self.models.get(model_name, self.models["balanced"])


model_registry = ModelRegistry()
