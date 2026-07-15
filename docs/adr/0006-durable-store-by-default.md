# ADR-0006: Durable Store by Default; Extract Persistence Selection

**Status**: Accepted
**Date**: 2026-07-15
**Amends**: ADR-0001

## Context

ADR-0001 records **"PostgreSQL checkpoints for persistence"** as the decision, and cites
"**Durability**: Resume from checkpoints" as a reason to choose LangGraph.

The code does something else. `main.py` makes Postgres **opt-in and secondary**: it defaults to
SQLite, and on *any* Postgres failure it silently downgrades:

```python
except Exception as exc:
    typer.echo(f"[checkpoint] Postgres unavailable ({type(exc).__name__}); falling back "
               "to local SQLite. Start it with: docker compose up -d postgres")
    db_url = ""
```

This is an **unrecorded decision reversal**. The fallback itself is good ergonomics — zero-infra
local dev is worth keeping. The problem is what it silently takes away.

**The bug.** Checkpointer and store are *different objects* with *different backends*. The SQLite
path pairs a durable `SqliteSaver` with a non-durable `InMemoryStore`. Per ADR-0005, the store is
where sentiment history lives. So on the default configuration:

- `sentiment_agent` needs ≥2 prior quarters and finds 0 → `sentiment_surprise` is **0.0 on every run**
- that zeroes the **0.20-weighted** tone term of the synthesis signal
- and caps `confidence` (`synthesis_agent.py:46` — `0.05 * n_quarters`)
- `delivery_agent` still *writes* tone to the store; the write is discarded at process exit, so
  history can never accumulate, run after run

**The scores are wrong, not merely unavailable.** `examples/AAPL-Q1-FY2025-brief.md:90` is the
receipt: *"Thin sentiment history: n_quarters = 0"*. The headline feature of the
`sentiment-surprise` skill silently no-ops on the configuration every developer runs.

**This is fixable at zero cost.** `langgraph.store.sqlite.SqliteStore` ships inside
`langgraph-checkpoint-sqlite`, **already a declared dependency**, and exposes the same
`from_conn_string` / `setup` surface as `PostgresStore`.

Separately, `main.py`'s backend block has a latent resource bug: if `PostgresStore` is entered
successfully but `PostgresSaver` (or either `.setup()`) throws, `store` is rebound to
`InMemoryStore` while the `PostgresStore` **stays registered in the `ExitStack`** — a live
connection held, unused, for the whole run.

## Decision

1. **Ratify SQLite-by-default for local dev.** ADR-0001's "PostgreSQL for persistence" is amended to
   "Postgres when `DATABASE_URL` is set; SQLite otherwise". The fallback stays.
2. **But both legs must be durable.** The SQLite path uses **`SqliteStore`**, not `InMemoryStore`.
   `InMemoryStore` is retained **only** for tests.
3. **Extract selection into `src/agentic_app/orchestration/checkpoint.py`**, exposing a
   `@contextmanager open_persistence(db_url, *, sqlite_path, report) -> (checkpointer, store)`.
   It reads no environment and imports no settings — `db_url` is a parameter. That is what makes it
   unit-testable without a database.
4. **Fix the orphaned connection.** Postgres backends are entered into a nested `ExitStack` and
   transferred with `stack.push(attempt.pop_all())` only once **both** are up. On any failure the
   nested stack unwinds and closes what it opened.

## Rationale

- **A default that silently produces wrong numbers is worse than one that fails.** Warning would
  leave the bug shipping; `SqliteStore` removes it for the price of one import.
- **Durability asymmetry is not obvious.** Nothing in "SQLite fallback" suggests *checkpoints
  persist but memory doesn't*. Making both legs durable removes the trap rather than documenting it.
- **`open_persistence` must be a context manager** because `graph.invoke` has to run *inside* the
  savers' scope. Yielding from inside the `ExitStack` preserves that lifetime exactly.
- **Transactional ownership** is the only way to guarantee a half-failed Postgres attempt leaks
  nothing.

## Alternatives Considered

- **Require Postgres; fail loudly if absent**: rejected — kills zero-infra local dev and contradicts
  the ergonomics the fallback was added for.
- **Keep `InMemoryStore` and warn loudly**: rejected — a ~10-line warning on every local run gets
  tuned out, and it leaves a known-wrong-numbers bug in place at *zero* saving, since `SqliteStore`
  needs no new dependency.
- **Leave the logic in `main.py` and just fix the store**: rejected — the block is untestable
  without a database, which is why the orphan bug survived unnoticed.
- **Return a plain tuple instead of a context manager**: rejected — a use-after-close waiting to
  happen (ADR-0001's "Durability" claim depends on the savers outliving the invoke).

## Consequences

- **Local runs accumulate real sentiment history**, so `sentiment_surprise` becomes non-zero from the
  third run of a ticker. **Signal scores will change.** Eval baselines must be re-recorded, and
  `examples/AAPL-Q1-FY2025-brief.md` regenerated — it currently documents the bug.
- **SQLite file locking** between `SqliteSaver` and `SqliteStore` sharing a path needs a decision
  (separate files, or one file with WAL). Must be settled when the swap lands.
- `main.py`'s `run()` drops from ~96 to ~30 lines and becomes purely CLI concerns.
- `orchestration/__init__.py` **must stay inert** — a convenience re-export of `checkpoint` would drag
  it into the hermetic trajectory test's import graph.
- ADR-0001's "Checkpoint storage (PostgreSQL) adds infrastructure" consequence is softened: Postgres
  is now optional for correctness, not just for convenience.
