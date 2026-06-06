"""Scoring functions for evals."""

from __future__ import annotations


def exact_match(expected: str, actual: str) -> float:
    """Exact match scoring."""
    return 1.0 if expected.lower() == actual.lower() else 0.0


def semantic_similarity(expected: str, actual: str) -> float:
    """Semantic similarity (placeholder)."""
    # Would use embeddings in production
    return 0.5
