# ADR-0001: Use LangGraph for Orchestration

**Status**: Accepted
**Date**: 2026-02-05

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
