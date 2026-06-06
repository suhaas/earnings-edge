# ADR-0003: Eval Gate in CI

**Status**: Accepted
**Date**: 2026-02-05

## Context

Agent quality can regress silently if prompts or tools change. We need a gate.

## Decision

Implement eval.yml as a required CI check:
- Runs on PR if `prompts/`, `src/agents/`, or `src/tools/` change
- Compares scores against main branch baseline
- Fails PR if regression detected (unless explicitly accepted)

## Rationale

- Early detection of prompt regressions
- Prevents shipping poor agent behavior
- Eval results attached to PR for transparency
- Fast feedback loop (evals cached via vcr replay)

## Alternatives Considered

- Post-deployment monitoring: Too late, already in prod
- Manual review: Human error, slow

## Consequences

- First-time setup of eval datasets required
- Eval.yml must complete before merge
- May require justification for regressions
