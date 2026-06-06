"""Tool trajectory scoring."""

from __future__ import annotations


def evaluate_trajectory(tools_used: list[str], expected: list[str]) -> float:
    """Score the sequence of tools called."""
    # Check if expected tools were used in order
    if tools_used == expected:
        return 1.0
    return 0.5 if set(tools_used) == set(expected) else 0.0
