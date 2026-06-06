"""Replay a production trace locally for debugging."""

from __future__ import annotations

import sys


def replay_trace(trace_id: str) -> None:
    """Re-run a captured production trace locally."""
    print(f"Replaying trace {trace_id}...")
    # Placeholder


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python replay_trace.py <trace_id>")
        sys.exit(1)
    replay_trace(sys.argv[1])
