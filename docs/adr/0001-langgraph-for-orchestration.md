# ADR-0001: Use LangGraph for Orchestration

**Status**: Accepted
**Date**: 2026-02-05
**Amended by**: ADR-0006 (persistence)

> **Amendment note (2026-07-15).** The core decision — LangGraph, StateGraph, conditional edges —
> still holds. Two claims below have drifted from the code:
>
> - **"PostgreSQL checkpoints for persistence"** — Postgres is opt-in, not the default. `main.py`
>   defaults to SQLite and falls back to it silently. **ADR-0006** ratifies that and fixes the
>   durability bug it caused.
> - **"Observability: Built-in LangSmith integration"** — true only when `LANGSMITH_TRACING=true`
>   (off by default); nothing in-repo consumes it. See **ADR-0010**.
>
> This ADR does **not** specify supervisor-vs-pipeline. The topology is a **fixed pipeline** with one
> conditional edge — see `docs/architecture.md`. That omission is why supervisor/researcher fossils
> survived across the docs for so long.

## Context

We need a scalable way to orchestrate multiple agents and define complex workflows.

## Decision

Use LangGraph (by LangChain) as the orchestration framework:
- StateGraph for agent topology
- Conditional edges for routing
- PostgreSQL checkpoints for persistence

## Rationale

- **State management**: Centralized, typed state (Pydantic)
- **Durability**: Resume from checkpoints
- **Observability**: Built-in LangSmith integration
- **Flexibility**: Easy to add new agents or edges

## Alternatives Considered

- Apache Airflow: Too heavy, designed for ETL not agent workflows
- Custom event loop: Too much engineering, no out-of-box persistence

## Consequences

- Strong dependency on LangGraph (mitigated via adapters)
- Checkpoint storage (PostgreSQL) adds infrastructure
- Testability requires graph fixtures
