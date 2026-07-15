# ADR-0005: Long-Term Memory via LangGraph BaseStore

**Status**: Accepted
**Date**: 2026-07-15
**Supersedes**: the deleted `skills/memory_management/SKILL.md`

## Context

`src/agentic_app/mcp/`, `rag/`, `memory/`, and `observability/` are all labelled
"stubs — `__init__.py` only (planned)" in `AGENTS.md:135` / `CLAUDE.md:194`.

For `memory/` that label is **wrong**. It is not planned — it is **done differently**, and the
decision was never written down.

The original design is recoverable from git. `skills/memory_management/SKILL.md`, deleted in
`94ede9c`, specified four capabilities:

> - **Short-term**: Windowed message history (token-budgeted)
> - **Long-term**: Persistent fact store (Redis/Postgres backed)
> - **Compaction**: Auto-summarize short-term memory when budget exceeded
> - **Retrieval**: Query memory by keyword or semantic similarity

The **same commit** that deleted that skill wired LangGraph's `BaseStore` end-to-end:

- `main.py` selects the backend (`PostgresStore` / `InMemoryStore`)
- `graph.py:34-35` injects it into any node declaring a `store` param
- `sentiment_agent.py:83` reads it — `store.search(("sentiment_history", ticker), limit=8)`
- `delivery_agent.py:74` writes it — `store.put(("sentiment_history", ticker), f"{year}Q{quarter}", ...)`

`skills/sentiment-surprise/SKILL.md` is the surviving spec, and it names `BaseStore` explicitly:

> "The Store is cross-thread; the checkpointer is per-thread — they are different objects."
> "Write the current quarter only AFTER successful delivery, to avoid polluting history on failed runs."

So the long-term half **shipped**, under a different name. The short-term half is **moot**:
`EarningsState` has no `messages` key, nodes are single-shot, and there are no "turns" or "session
state" for windowed history or compaction to apply to. This is a batch pipeline, not a chat agent.

## Decision

**Long-term memory is LangGraph `BaseStore`.** Namespace `("sentiment_history", <ticker>)`, key
`f"{year}Q{quarter}"`, value `{"tone": float}`. Written by `delivery_agent` after successful
delivery; read by `sentiment_agent` to compute the trailing-mean tone surprise.

**Short-term memory is not applicable** to a stateless single-shot pipeline. If a conversational
surface is ever added, revisit — do not pre-build it.

**Delete `src/agentic_app/memory/`** and retire the "planned" label in `AGENTS.md`, `CLAUDE.md`, and
`.github/copilot-instructions.md`.

## Rationale

- **It already works.** The store is injected, read, and written on every run. A `memory/` module
  would re-solve a solved problem and give two competing answers to "where does memory live?".
- **`BaseStore` is the framework's own answer** — cross-thread by design, with a Postgres backend we
  already run for checkpoints. The deleted skill's "Redis/Postgres backed" requirement is satisfied
  without new infrastructure.
- **The "planned" label is a lie with a cost.** It tells every agent reading `CLAUDE.md` that memory
  is unbuilt, inviting someone to build it — beside the working implementation.

## Alternatives Considered

- **Build `memory/` as specced**: rejected — the short-term half has no consumer (no `messages`, no
  turns), and the long-term half would duplicate `BaseStore`.
- **Keep `memory/` as a thin facade over `BaseStore`**: rejected — indirection with no second
  implementation to abstract over. `graph.py` injects the store directly by signature; a facade
  could not sit in that path without fighting the framework.
- **Leave the stub and the "planned" label alone**: rejected — that is the status quo that produced
  this ADR.

## Consequences

- `src/agentic_app/memory/` is deleted. The docs' "planned" list loses one entry.
- **The Store is only durable on Postgres.** The SQLite default yields `InMemoryStore`, so
  `sentiment_surprise` reads 0.0 on every local run — see **ADR-0006**, which this ADR forces.
- The namespace/key format is duplicated in three places — `delivery_agent.py:74`,
  `sentiment_agent.py:83`, and `tests/integration/test_trajectory.py` — with no shared constant.
  Accepted for now; a drift risk worth a follow-up.
- Anyone wanting conversational memory later must revisit this ADR rather than assume `memory/` was
  merely unfinished.
