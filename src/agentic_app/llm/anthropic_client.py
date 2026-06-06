"""LLM client: Anthropic API wrapper."""

from __future__ import annotations


class AnthropicClient:
    """Async Anthropic client wrapper."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
