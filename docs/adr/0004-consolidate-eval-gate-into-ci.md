# ADR-0004: Consolidate the Eval Gate into ci.yml

**Status**: Accepted
**Date**: 2026-06-07
**Supersedes**: ADR-0003

## Context

ADR-0003 introduced a standalone `eval.yml` workflow as the agent eval gate. In
practice the repository ended up with **two** overlapping eval mechanisms: `eval.yml`
*and* an `eval-gate` job inside `ci.yml`. Both ran the eval suite and both posted a
comment to the PR, producing duplicate comments.

`eval.yml` had also drifted out of sync with the codebase and was effectively broken:

- **Wrong path filters**: triggered on `src/agents/**` and `src/tools/**`, but the
  package is `src/agentic_app/agents/**` / `src/agentic_app/tools/**` — so it never fired.
- **Arg mismatch**: invoked `python evals/run.py --baseline … --output eval-report.json`,
  but `run.py` takes no such flags and writes `eval-results.json`, so the report the next
  step read never existed.
- **Bare `python`** instead of `uv run python` — the uv-managed venv is not on `PATH` in
  CI, the same failure mode that broke the `make` jobs.
- **Missing `pull-requests: write`** permission → the comment step 403'd.
- **Deprecated** `actions/upload-artifact@v3`.

## Decision

Remove `eval.yml`. The **`eval-gate` job in `ci.yml`** is the single eval gate:

- Runs on every pull request (`if: github.event_name == 'pull_request'`).
- Runs `make eval` (→ `uv run python evals/run.py`).
- Has `permissions: pull-requests: write` and posts the eval report as a PR comment.

All documentation references were updated from `eval.yml` to "the `eval-gate` job in
`ci.yml`". This ADR supersedes ADR-0003.

## Rationale

- **Single source of truth** — one workflow file owns CI; no divergence between two
  eval definitions.
- **No duplicate PR comments**.
- **Consistent tooling** — every job runs tools through `uv run`, matching lint/test.
- **Lower maintenance** — one place to evolve when the real eval suite lands.

## Alternatives Considered

- **Make `eval.yml` canonical and drop `ci.yml`'s eval-gate**: rejected — `ci.yml`
  already centralizes `lint`, `prompt-checks`, and `test`, so the eval gate belongs
  alongside them.
- **Keep both and just fix the path filter**: rejected — leaves the duplication and the
  double-comment problem, and "fixing the path" alone would turn a dormant broken
  workflow into an actively failing one.

## Consequences

- The eval gate now runs on **every** PR (no path filter). Simpler and safe while
  `evals/run.py` is cheap; revisit a path filter if the real suite becomes expensive.
- `evals/run.py` is currently a **placeholder** that passes (exit 0); the
  baseline-comparison logic in `scripts/check_eval_regression.py` is **not yet wired in**.
  Implementing the real eval suite + baseline comparison is follow-up work — at which
  point `PLACEHOLDER` in `run.py` is flipped to `False`.
- ADR-0003 is superseded; its `eval.yml`-specific mechanics no longer apply.
