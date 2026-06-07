"""Tool input/output Pydantic schemas."""

from __future__ import annotations

from typing import Any


class ToolError(Exception):
    """Base exception for tool errors."""

    def __init__(self, category: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.category = category
        self.message = message
        self.details = details or {}
        super().__init__(f"[{category}] {message}")
