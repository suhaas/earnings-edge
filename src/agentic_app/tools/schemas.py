"""Tool input/output Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ToolError(Exception):
    """Base exception for tool errors."""

    def __init__(self, category: str, message: str, details: dict | None = None) -> None:
        self.category = category
        self.message = message
        self.details = details or {}
        super().__init__(f"[{category}] {message}")
