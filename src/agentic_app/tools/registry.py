"""Tool registry and definitions."""

from __future__ import annotations


class ToolRegistry:
    """Central registry for tools."""

    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def register(self, func: Any) -> Any:
        """Register a tool."""
        self.tools[func.__name__] = func
        return func


tool_registry = ToolRegistry()
