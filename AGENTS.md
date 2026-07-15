# earnings-edge: Agent Development Guidelines

This project implements a multi-agent AI system for financial analysis and earnings research. All development must adhere to these conventions. Also see `.github/copilot-instructions.md` for Copilot-specific guidance and `docs/` for runbooks.

> **Accuracy note**: sections marked *(planned — not implemented)* describe intended design whose
> modules do not exist yet. Everything else reflects code on disk. If you build or move a module,
> update this file **and** `.github/copilot-instructions.md` (they are near-duplicates) in the same change.

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
  Pydantic models `EarningsKPIs` + `SurpriseSignal` live here too.
- **Persistence**: selected at runtime in `src/agentic_app/main.py` (there is **no** `checkpoints.py`).
  `DATABASE_URL` starting with `postgres` → `PostgresSaver` + `PostgresStore` (`.setup()` creates tables);
  otherwise local `SqliteSaver` (`earningsedge.db`) + `InMemoryStore`. Unreachable Postgres falls back to
  SQLite with a warning. `thread_id` is `f"{ticker}-{year}-Q{quarter}"`.

### Agent Roles

One module per node in `src/agentic_app/agents/`, each a **sync** `*_node(state) -> dict`:

- **Ingestion** (`ingestion_agent.py`): fetches transcript / press-release text into state
- **Sentiment** (`sentiment_agent.py`): tone analysis; reads the Store (injected automatically)
- **KPI** (`kpi_agent.py`): extracts structured `EarningsKPIs` (revenue, EPS, guidance, segments)
- **Synthesis** (`synthesis_agent.py`): fuses sentiment + KPIs into `signal` + `brief_markdown`
- **Evaluation** (`evaluation_agent.py`): scores grounding; `route_after_eval` returns `revise` or `deliver`
- **Delivery** (`delivery_agent.py`): final output; reads + writes the Store

`base.py` provides `BaseAgent`. Sentiment and KPI run **concurrently** — never assume one sees the other's output.

### Tools & Skills Boundary

- **Tools** (`src/agentic_app/tools/`): `registry.py` (`ToolRegistry`) + Pydantic schemas in `schemas.py`
- **Skills** (`skills/`): Multi-step workflows with bundled instructions + assets; agents load dynamically.
  Real skills are domain-specific: `kpi-extraction`, `finbert-tone-analysis`, `sec-edgar-8k-retrieval`,
  `signal-synthesis-scoring`, `grounding-faithfulness-eval`, `composio-delivery`, and others.
- **MCP** *(planned — not implemented)*: `src/agentic_app/mcp/` is a stub (`__init__.py` only).
  The venv does ship `edgartools-mcp` as an external server.

### RAG Pipeline *(planned — not implemented)*

`src/agentic_app/rag/` is a stub (`__init__.py` only). No ingest, chunking, embeddings, retriever, or
vectorstore module exists, despite `VECTORDB_*` / `CHUNK_*` / `RETRIEVAL_*` vars in `.env.example`, a
`qdrant` service in `docker-compose.yml`, and `scripts/seed_vectorstore.py`. Intended design:
structure-aware chunk → embed → upsert; hybrid search + rerank behind a swappable pgvector/Qdrant Protocol.

---

## Code Style & Typing

### Python

- **All files**: Python 3.11+ (`requires-python = ">=3.11"`; the venv is 3.12), strict typing (`from __future__ import annotations`)
- **Sync, not async**: graph nodes are plain `def`. There is no async code in the agent path today — do
  not introduce `async def` nodes without changing how the graph is invoked.
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
  (the Typer CLI in `main.py` uses `typer.echo` for user-facing output)

---

## Project Structure

```text
src/agentic_app/
├── main.py                # Typer CLI: `run`; picks checkpointer/store from DATABASE_URL
├── api/                   # app.py — GET /health ONLY (no /chat, no SSE)
├── config/                # settings.py, models.py (MODEL REGISTRY), logging.py
├── agents/                # base.py + ingestion, sentiment, kpi, synthesis, evaluation, delivery
├── orchestration/         # graph.py (StateGraph wiring), state.py (EarningsState)
├── tools/                 # registry.py, schemas.py
├── llm/                   # anthropic_client.py — STUB (agents call ChatAnthropic directly)
├── prompts/               # loader.py (resolves role → active version from prompts/registry.yaml)
└── mcp/ rag/ memory/ observability/    # stubs — __init__.py only (planned)

prompts/                   # Versioned system prompts (immutable once shipped)
├── registry.yaml          # Maps role → ACTIVE version + metadata
├── shared/                # safety.md, output_formats.md, tool_use_policy.md
├── ingestion/, kpi/, sentiment/, synthesis/, evaluation/, delivery/
│   └── v1.md, v2.md, ... (each version is immutable)

skills/                    # Agent runtime skills (on-demand workflows)
├── README.md              # Explains SKILL.md convention + agent loading
├── kpi-extraction/, finbert-tone-analysis/, sec-edgar-8k-retrieval/,
    signal-synthesis-scoring/, grounding-faithfulness-eval/, composio-delivery/, ...

evals/                     # First-class eval harness
├── datasets/              # end_to_end.jsonl, researcher_qa.jsonl
├── scorers/               # llm_judge.py, trajectory.py
├── suites/                # regression.yaml
└── run.py                 # Eval runner (used by the ci.yml eval-gate job)

tests/
├── conftest.py            # Fixtures: fake_anthropic, in_memory_store, frozen_clock
├── fixtures/
├── unit/                  # NO network, NO LLM calls, mocked everything
├── integration/           # Hermetic graph wiring (fake agent modules + MemorySaver)

scripts/                   # replay_trace.py, seed_vectorstore.py, check_*.py
data/ examples/            # Fixtures, caches, sample briefs
```

---

## Build & Test

### Local Development

```bash
make install   # uv sync --all-extras
make lint      # uv run ruff check + uv run mypy
make format    # uv run ruff format + --fix
make test      # uv run pytest tests/ -v
make eval      # uv run python evals/run.py
make run       # uv run python -m agentic_app.main run
make trace     # LANGSMITH_TRACING=true + OTEL endpoint, then run
```

See `Makefile` for all targets; `make help` lists them.

Every target shells through `uv run`, which syncs the env first. **`UV_SYSTEM_CERTS=1` is required** on
this machine (TLS-inspecting proxy). The venv has **no pip** by design (uv-created): `pip` on PATH
resolves to the *global* interpreter and ignores `VIRTUAL_ENV`, so `pip install` silently pollutes it.
Use `uv add` (declares + locks) or `uv pip install` (ad hoc).

### Docker

```bash
docker build -t earnings-edge:latest .
docker-compose up          # app + qdrant + postgres + OTel collector
```

### CI/CD Gates

- **`ci.yml`**: Lint + type-check + unit/integration tests on every PR
- **`ci.yml` `eval-gate` job**: AGENT EVAL GATE — runs eval suite, fails on score regression vs. main
- **`prompt-diff.yml`**: Detects changes under `prompts/` and forces eval run + human review
- **`release.yml`**: Build + push image, tag, changelog

---

## Prompts & Versioning

### The Registry

- **`prompts/registry.yaml`**: Source of truth for which prompt versions are active per role
- **Immutable versioning**: Once `v1.md` is shipped, never edit it; bump to `v2.md` for changes
- **Author + eval score**: Stored in registry metadata so you can track which version won
- **Format**: Fragments composed via `src/agentic_app/prompts/loader.py`; includes shared guardrails +
  role-specific logic. Drift is gated by `tests/unit/test_prompt_loader.py`,
  `tests/unit/test_prompt_registry.py`, the `prompt-consistency` pre-commit hook, and CI.

### Prompt Development

1. Draft in `docs/prompt-templates/` (experiments)
2. Version into `prompts/{role}/vN.md` (immutable)
3. Update `prompts/registry.yaml` to activate
4. Push → triggers `prompt-diff.yml` → eval gate → human review

---

## Tools & Tool Use

### Defining a Tool

1. Create `src/agentic_app/tools/{capability}.py` with a function decorated `@tool_registry.register`
   (bare — `ToolRegistry.register(self, func)` takes the function directly, **not** `register()`)
2. Define schema in `src/agentic_app/tools/schemas.py` as a Pydantic model
3. `registry.py` exports Anthropic-format schemas
4. **Test**: Unit test in `tests/unit/test_tools/`; no side effects in tests

### Handling Tool Errors

- Wrap errors with context rather than swallowing them
- Append the failure to `state["errors"]` so it survives the graph run
- The **evaluation** node decides `revise` vs `deliver` — there is no separate critic

---

## Testing & Evaluation

### Unit Tests

- **Location**: `tests/unit/` (`test_prompt_loader.py`, `test_prompt_registry.py`, `test_tools/`)
- **Constraints**: NO network, NO LLM calls, NO side effects
- **Fixtures**: `fake_anthropic`, `in_memory_store`, `frozen_clock` in `conftest.py`
- **Run**: `make test` or `uv run pytest tests/unit/`

### Integration Tests

- **Location**: `tests/integration/` (`test_trajectory.py`, `test_example.py`)
- **Setup**: **Hermetic** — `test_trajectory.py` injects fake agent modules into `sys.modules` *before*
  `graph.py` imports them, then compiles with a real `MemorySaver` + `InMemoryStore`. This tests graph
  wiring with no network. (Note: `vcrpy` is **not** a dependency; "vcr-recorded responses" in older
  docstrings is aspirational.)
- **Run**: `make test` or `uv run pytest tests/integration/`

### Eval Suites

- **Location**: `evals/`
- **Datasets**: Versioned JSONL in `evals/datasets/` (inputs + expected outcomes/rubrics)
- **Scorers**: `evals/scorers/llm_judge.py`, `evals/scorers/trajectory.py`
- **Suites**: `evals/suites/regression.yaml` binds dataset → agent → scorer → threshold
- **Run**: `make eval` (locally) or the `ci.yml` `eval-gate` job on PR
- **Regression gate**: If score < threshold, PR fails; fix prompt or accept regression with justification

---

## Key Gotchas & Patterns

### Agent Loops

- The self-correction loop is `evaluate → revise → evaluate`. `route_after_eval` decides; `revision_count`
  is bumped in the `revise` node wrapper (`_bump_and_synth` in `graph.py`) and bounds the loop.
  There is no supervisor and no step budget in state.
- **Runbook**: See `docs/runbooks/agent-stuck-in-loop.md`

### Prompt Rollback

- **Active version** in `prompts/registry.yaml` points to the live v{N}.md
- **Fast rollback**: Edit registry to point to previous version; no code redeploy
- **Runbook**: See `docs/runbooks/rollback-a-prompt.md`

### Rate Limits *(planned — not implemented)*

No `llm/retry.py` and no circuit breaker exist; `src/agentic_app/llm/` contains only
`anthropic_client.py`. Intended: exponential backoff on `RateLimitError`, fast-fail after N failures.

### Tracing & Debugging

- **LangSmith**: env-gated via `LANGSMITH_TRACING`; see `make trace`. Note the LangSmith SDK trips over
  this machine's TLS-inspecting proxy — keep network calls out of the default test path.
- **OpenTelemetry**: OTel collector exists in `docker-compose.yml`; `OTEL_EXPORTER_OTLP_ENDPOINT` is
  wired in `make trace`. *(No `observability/` module yet — it is an empty stub, so there are no
  Prometheus metrics and no `@traced` decorator despite the env vars.)*
- **Replay**: `scripts/replay_trace.py` re-runs a captured trace locally
- **Time-travel debugging**: checkpoints chain via `parent_checkpoint_id` within a `thread_id`

### Checkpoint Schema (created by `langgraph-checkpoint-postgres`, not by us)

`checkpoints` (PK `thread_id, checkpoint_ns, checkpoint_id`; `checkpoint`/`metadata` JSONB;
`parent_checkpoint_id` chains history), `checkpoint_blobs` (PK `thread_id, checkpoint_ns, channel,
version`; `BYTEA`), `checkpoint_writes` (PK `thread_id, checkpoint_ns, checkpoint_id, task_id, idx`),
`checkpoint_migrations` (`v`). Inspect via `docker compose exec postgres psql -U agentic -d earnings_edge`
— the `postgres:16-alpine` image already ships `psql`, so no host install is needed.

### API Surface

`src/agentic_app/api/app.py` exposes **only `GET /health`**. There is no `/chat` endpoint and no SSE
streaming, despite `ENABLE_STREAMING` / `API_*` vars in `.env.example`. The real entrypoint is the
Typer CLI: `python -m agentic_app.main run --ticker NVDA --year 2025 --quarter 4`.

---

## Observability

- **Logs**: Structured JSON via `structlog`; see `src/agentic_app/config/logging.py`
- **Traces**: LangSmith + OpenTelemetry, env-gated *(no in-repo module yet)*
- **Metrics** *(planned)*: Prometheus counters for tokens, latency, tool calls, eval scores
- **Stack**: Postgres (checkpoints + store), Qdrant, OTel collector

---

## Common Agent Tasks

| Task | Command | Notes |
|------|---------|-------|
| Add a new worker agent | Create `src/agentic_app/agents/{role}_agent.py` exposing `{role}_node`; add the node + edges in `orchestration/graph.py` | No router to update — edges are explicit |
| Add a tool | Create `src/agentic_app/tools/{capability}.py`; schema in `schemas.py`; register via `@tool_registry.register` | Bare decorator, no parens |
| Update a prompt | Draft in `docs/prompt-templates/`; version into `prompts/{role}/vN.md`; update `registry.yaml` | Triggers eval gate |
| Fix a failing eval | Debug locally with `scripts/replay_trace.py`; update agent/tool logic; re-run `make eval` | Commit eval score improvement |
| Deploy | Push to main; CI runs lint + tests + eval; merge if green; `release.yml` builds + pushes image | Check CODEOWNERS for prompt changes |

---

## Links

- **Architecture**: `docs/architecture.md`
- **ADRs**: `docs/adr/` (immutable decisions)
- **Runbooks**: `docs/runbooks/` (on-call playbooks)
- **Tests**: `tests/README.md`
- **Evals**: `evals/README.md`
