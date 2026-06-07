"""Eval runner: executes suites, compares against baseline, exits non-zero on regression."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Regression threshold: fail the gate only if the current score drops more than this
# below baseline (kept here so it stays explicit when the real suite is wired in).
REGRESSION_TOLERANCE = 0.0

# Placeholder mode: no real eval suite is wired yet, so the gate does NOT fail CI.
# Flip to False once evals/suites are implemented and produce real scores below.
PLACEHOLDER = True


def run_evals() -> int:
    """Run the eval suite, write a report, and return an exit code.

    Returns 0 on pass, 1 on a real regression. While ``PLACEHOLDER`` is True the
    gate is informational only (always 0) so it doesn't block every PR with a
    stub score.
    """
    if PLACEHOLDER:
        print("Running evals (placeholder - no real suite wired yet; gate is informational).")
        results = {
            "status": "placeholder",
            "baseline_score": None,
            "current_score": None,
            "delta": 0.0,
        }
        Path("eval-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        return 0

    # Real suite goes here: load evals/suites/*, run agents, score vs. baseline.
    baseline_score = 0.0
    current_score = 0.0
    delta: float = current_score - baseline_score

    results = {
        "status": "ok",
        "baseline_score": baseline_score,
        "current_score": current_score,
        "delta": delta,
    }
    Path("eval-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Eval delta: {delta:+.3f} (tolerance {-REGRESSION_TOLERANCE:+.3f})")
    return 1 if delta < -REGRESSION_TOLERANCE else 0


if __name__ == "__main__":
    sys.exit(run_evals())
