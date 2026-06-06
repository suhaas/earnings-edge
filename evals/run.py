"""Eval runner: executes suites, compares against baseline, exits non-zero on regression."""

from __future__ import annotations

import json
import sys


def run_evals() -> int:
    """Run eval suite and return exit code."""
    print("Running evals...")
    # Placeholder implementation
    results = {"baseline_score": 0.85, "current_score": 0.82, "delta": -0.03}
    with open("eval-results.json", "w") as f:
        json.dump(results, f)
    
    # Fail if regression
    return 1 if results["delta"] < 0 else 0


if __name__ == "__main__":
    sys.exit(run_evals())
