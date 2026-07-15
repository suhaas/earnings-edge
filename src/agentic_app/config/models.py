"""Model registry: logical name → pinned model ID.

NOT WIRED YET: `get()` has zero callers, so these tier names are unreachable. The agents
name their model inline in `ChatAnthropic(model=...)` (see agents/kpi_agent.py,
synthesis_agent.py, delivery_agent.py, evaluation_agent.py).

Wiring them up is not a pure ID swap: `balanced` and `deep` reject `temperature` with a
400 ("temperature is deprecated for this model"); only `cheap` still accepts it. The
agents currently pass temperature=0 / 0.2, which must be dropped first.
"""

from __future__ import annotations


class ModelRegistry:
    """Central registry for model selection by role."""

    # Pinned IDs — these are complete as-is; never append a date suffix.
    models = {
        "cheap": "claude-haiku-4-5",
        "balanced": "claude-sonnet-5",
        "deep": "claude-opus-4-8",
    }

    def get(self, model_name: str) -> str:
        """Get model ID by logical name."""
        return self.models.get(model_name, self.models["balanced"])


model_registry = ModelRegistry()
