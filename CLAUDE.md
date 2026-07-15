# earnings-edge: Project Memory for Claude Code

This document is loaded at session start and contains architecture, commands, conventions, verification loops, and gotchas.

> **Accuracy note**: sections marked *(planned — not implemented)* describe intended design whose
> modules do not exist yet. Everything else reflects code on disk. Keep it that way: if you build or
> move a module, update this file in the same change.

---

## Architecture & Core Concepts

### The Graph
- **Orchestration**: LangGraph StateGraph with nodes = agents, edges = handoffs
- **Topology** (`src/agentic_app/orchestration/graph.py`): a fixed pipeline, *not* a supervisor/router:
  ```text
  ingest --> {sentiment, kpi}      (parallel fan-out)
  {sentiment, kpi} --> synthesize  (fan-in: waits for BOTH)
  synthesize --> evaluate
  evaluate --(route_after_eval)--> revise --> evaluate   (self-correction loop)
                                \-> deliver --> END
  ```
- **State** (`src/agentic_app/orchestration/state.py`): `EarningsState` TypedDict — ticker/year/quarter,
  transcripts, `sentiment` + `kpis` (both `Annotated[..., operator.add]` so parallel branches merge),
  `signal`, `brief_markdown`, `grounding_score`, `revision_count`, `delivery_log`, `errors`.
  Pydantic models `EarningsKPIs` and `SurpriseSignal` live here too.
- **Persistence**: chosen at runtime in `src/agentic_app/main.py` (there is **no** `checkpoints.py` module).
  `DATABASE_URL` starting with `postgres` → `PostgresSaver` + `PostgresStore`, with `.setup()` creating
  tables on first run; anything else → local `SqliteSaver` (`earningsedge.db`) + `InMemoryStore`.
  An unreachable Postgres falls back to SQLite with a warning rather than hard-failing.
  `thread_id` is `f"{ticker}-{year}-Q{quarter}"`.

### Agent Roles
One module per node in `src/agentic_app/agents/`, each a **sync** `*_node(state) -> dict`:
- **Ingestion** (`ingestion_agent.py`): fetches transcript / press-release text into state
- **Sentiment** (`sentiment_agent.py`): tone analysis; reads the Store (injected automatically)
- **KPI** (`kpi_agent.py`): extracts structured `EarningsKPIs` (revenue, EPS, guidance, segments)
- **Synthesis** (`synthesis_agent.py`): fuses sentiment + KPIs into `signal` + `brief_markdown`
- **Evaluation** (`evaluation_agent.py`): scores grounding; `route_after_eval` returns `revise` or `deliver`
- **Delivery** (`delivery_agent.py`): final output; reads + writes the Store

Sentiment and KPI run **concurrently** — never assume one sees the other's output.

### Tools & Skills Boundary
- **Tools** (`src/agentic_app/tools/`): `registry.py` + Anthropic schemas in `schemas.py`
- **Skills** (`skills/`): Multi-step workflows with bundled instructions + assets; agents load dynamically
- **MCP** *(planned — not implemented)*: `src/agentic_app/mcp/` is a stub (`__init__.py` only).
  Note the venv does ship `edgartools-mcp` as an external server.

### RAG Pipeline *(planned — not implemented)*
`src/agentic_app/rag/` is a stub (`__init__.py` only). No ingest, retriever, or vectorstore module
exists yet, despite `VECTORDB_*` / `CHUNK_*` / `RETRIEVAL_*` vars in `.env.example` and a `qdrant`
service in `docker-compose.yml`. Intended design: structure-aware chunk → embed → upsert; hybrid
search + rerank behind a swappable pgvector/Qdrant Protocol.

---

## Code Style & Typing

### Python
- **All files**: Python 3.11+ (`requires-python = ">=3.11"`; the venv is 3.12), strict typing (`from __future__ import annotations`)
- **Sync, not async**: graph nodes are plain `def`. There is no async code in the agent path today —
  do not introduce `async def` nodes without changing how the graph is invoked.
- **Functions**: Type-annotated arguments and returns; use `Pydantic` for complex inputs/outputs
- **Error handling**: accumulate failures into `state["errors"]` (an `operator.add` list) rather than
  raising through a node; typed exceptions at tool boundaries
- **Imports**: src-layout — `packages = ["src/agentic_app"]`; import absolutely (`from agentic_app.x import y`); organize stdlib → third-party → local

### Naming
- **Agents**: `{role}_agent.py` exposing `{role}_node` (e.g., `kpi_agent.py` → `kpi_node`)
- **Tools**: `{capability}.py`
- **Skills**: `{skill_domain}/SKILL.md` + `{skill_domain}/scripts/`, `{skill_domain}/resources/`
- **Prompts**: `prompts/{role}/v{N}.md` (immutable; version in `prompts/registry.yaml`).
  Roles: `ingestion`, `kpi`, `sentiment`, `synthesis`, `evaluation`, `delivery`, `shared`.

### Linting & Format
- **Ruff**: `check` + `format`; configured in `pyproject.toml`
- **MyPy**: `strict = true`; see `pyproject.toml`
- **Pre-commit**: ruff-check, ruff-format, mypy, gitleaks, prompt-consistency (`.pre-commit-config.yaml`)
- **CI/CD**: `make lint` runs checks; push only after passing

---

## Configuration

### Secrets & Env
- **No hardcoded secrets**; use `pydantic-settings` in `src/agentic_app/config/settings.py`
- **`settings.py`**: typed env loader. Requires `anthropic_api_key`, `database_url`, `vectordb_url`.
  ⚠️ `main.py run` does **not** go through `Settings` — it reads `DATABASE_URL` from `os.environ`
  directly after `load_dotenv()`, which is why a commented-out `DATABASE_URL` still runs (on SQLite).
- **`models.py`**: MODEL REGISTRY (logical name → pinned model ID); `cheap` = `claude-haiku-4-5`,
  `balanced` = `claude-sonnet-5`, `deep` = `claude-opus-4-8`; unknown names fall back to `balanced`.
  ⚠️ **Not wired**: nothing imports `model_registry`, so the tier names are unreachable — `get()` has
  zero callers and no env var selects a tier. The agents name the model inline instead:
  `ChatAnthropic(model="claude-sonnet-4-5", temperature=...)` in `kpi_agent.py`, `synthesis_agent.py`,
  `delivery_agent.py`, and `evaluation_agent.py`. Routing them through `get()` is **not** a pure ID
  swap: `balanced` (Sonnet 5) and `deep` (Opus 4.8) both reject `temperature` with
  `400 — "temperature is deprecated for this model"` (verified against the live API); only `cheap`
  (Haiku 4.5) still accepts it. Drop the `temperature=0` / `temperature=0.2` args first.
- **`.env`**: git-ignored; copy from `.env.example`. Postgres credentials must match
  `docker-compose.yml` (`agentic` / `dev-password` / `earnings_edge`).

### Logging
- **Structured logs** via `structlog` (JSONRenderer) in `src/agentic_app/config/logging.py`
- **No print()**; use `logger` from `src/agentic_app/config/logging.py`
  (note: the Typer CLI in `main.py` uses `typer.echo` for user-facing output)

---

## Build & Test Commands

```bash
make install   # uv sync --all-extras
make lint      # uv run ruff check + uv run mypy
make format    # uv run ruff format + --fix
make test      # uv run pytest tests/ -v
make eval      # uv run python evals/run.py
make run       # uv run python -m agentic_app.main run
make trace     # LANGSMITH_TRACING=true + OTEL endpoint, then run
```

Every target shells through `uv run`, which syncs the env first. **`UV_SYSTEM_CERTS=1` is required**
on this machine (TLS-inspecting proxy) — it is set for Claude Code in `.claude/settings.json`.

⚠️ The venv has **no pip**, by design (uv-created). `pip` on PATH resolves to the *global* Python 3.12
and ignores `VIRTUAL_ENV`, so `pip install` silently pollutes the global interpreter.
Use `uv add` (declares + locks) or `uv pip install` (ad hoc).

---

## Verification Loop (Claude Code Workflow)

1. **Code change**: Edit file → auto-save triggers format-on-save
2. **Local validation**: `make lint` (ruff + mypy) before pushing
3. **Test locally**: `make test` (unit + integration)
4. **Eval gate**: `make eval` to validate against baseline
5. **Push**: Triggers CI/CD (`ci.yml` — lint, prompt-checks, test, eval-gate; also `prompt-diff.yml`, `release.yml`)
6. **Human review**: Check CODEOWNERS for prompt changes

---

## Key Gotchas & Patterns

### Agent Loops
- The self-correction loop is `evaluate → revise → evaluate`. `route_after_eval` decides; `revision_count`
  is bumped in the `revise` node wrapper (`_bump_and_synth` in `graph.py`) and bounds the loop.
  There is no supervisor and no step budget in state.
- **Runbook**: See `docs/runbooks/agent-stuck-in-loop.md`

### Prompt Rollback
- **Active version** in `prompts/registry.yaml` points to the live v{N}.md; loaded by `src/agentic_app/prompts/loader.py`
- **Fast rollback**: Edit registry to point to previous version; no code redeploy
- **Runbook**: See `docs/runbooks/rollback-a-prompt.md`

### Rate Limits *(planned — not implemented)*
No `llm/retry.py` and no circuit breaker exist; `src/agentic_app/llm/` contains only
`anthropic_client.py`. Intended: exponential backoff on `RateLimitError`, fast-fail after N failures.

### Tracing & Debugging
- **LangSmith**: env-gated via `LANGSMITH_TRACING`; see `make trace`
- **OpenTelemetry**: OTel collector exists in `docker-compose.yml`; `OTEL_EXPORTER_OTLP_ENDPOINT` is
  wired in `make trace`. *(No `src/agentic_app/observability/` module yet — it is an empty stub, so
  there are no Prometheus metrics despite the env vars.)*
- **Replay**: `scripts/replay_trace.py` re-runs a captured trace locally
- **Time-travel debugging**: Postgres/SQLite checkpoints allow resuming from past states; checkpoints
  chain via `parent_checkpoint_id` within a `thread_id`

### Checkpoint Schema (created by `langgraph-checkpoint-postgres`, not by us)
`checkpoints` (PK `thread_id, checkpoint_ns, checkpoint_id`; `checkpoint`/`metadata` JSONB;
`parent_checkpoint_id` chains history), `checkpoint_blobs` (PK `thread_id, checkpoint_ns, channel,
version`; `BYTEA`), `checkpoint_writes` (PK `thread_id, checkpoint_ns, checkpoint_id, task_id, idx`),
`checkpoint_migrations` (`v`). Inspect via `docker compose exec postgres psql -U agentic -d earnings_edge`
— the `postgres:16-alpine` image already has `psql`, so no host install is needed.

### API Surface
`src/agentic_app/api/app.py` currently exposes **only `GET /health`**. There is no `/chat` endpoint
and no SSE streaming, despite `ENABLE_STREAMING` / `API_*` vars in `.env.example`. The real entrypoint
is the Typer CLI: `python -m agentic_app.main run --ticker NVDA --year 2025 --quarter 4`.

---

## Project Structure at a Glance

```text
src/agentic_app/
  agents/         # ingestion, sentiment, kpi, synthesis, evaluation, delivery (+ base)
  orchestration/  # graph.py (StateGraph wiring), state.py (EarningsState)
  config/         # settings.py, models.py (registry), logging.py
  llm/            # anthropic_client.py — STUB (agents call ChatAnthropic directly)
  prompts/        # loader.py (reads prompts/registry.yaml)
  tools/          # registry.py, schemas.py
  api/            # app.py (GET /health only)
  main.py         # Typer CLI; selects checkpointer/store from DATABASE_URL
  mcp/ rag/ memory/ observability/   # stubs — __init__.py only
prompts/          # Versioned system prompts (immutable) + registry.yaml
skills/           # Agent runtime skills + workflows
evals/            # Evaluation datasets, scorers, suites
tests/            # Unit + integration tests
docs/             # architecture.md, adr/, runbooks/
scripts/          # replay_trace.py, seed_vectorstore.py, check_*.py
data/ examples/   # Fixtures, caches, sample briefs
```

---

## Links

- **Full guide**: `.github/copilot-instructions.md` (Copilot-centric) or `AGENTS.md` (agent-centric)
- **Architecture**: `docs/architecture.md`
- **ADRs**: `docs/adr/` (immutable decisions)
- **Runbooks**: `docs/runbooks/` (on-call playbooks)
- **Tests**: `tests/README.md`
- **Evals**: `evals/README.md`
