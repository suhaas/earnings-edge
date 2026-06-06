"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def fake_anthropic():
    """Fake Anthropic client for tests (no API calls)."""
    # Placeholder
    return None


@pytest.fixture
def in_memory_store():
    """In-memory vector store for tests."""
    # Placeholder
    return {}


@pytest.fixture
def frozen_clock(monkeypatch):
    """Frozen clock for deterministic tests."""
    # Placeholder
    return None
