"""Shared graph state schema (Pydantic)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class GraphState(BaseModel):
    """Shared state for the agent graph."""

    messages: list[dict[str, Any]] = []
    scratchpad: dict[str, Any] = {}
    routing_decision: str | None = None
    step_count: int = 0
    token_budget: int = 10000
