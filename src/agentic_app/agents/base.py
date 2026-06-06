"""Base agent class."""

from __future__ import annotations


class BaseAgent:
    """Base class for all agent implementations."""

    def __init__(self, role: str) -> None:
        """Initialize agent with a role."""
        self.role = role
