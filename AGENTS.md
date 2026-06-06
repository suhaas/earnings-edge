# earnings-edge: Agent Development Guidelines

This project implements a multi-agent AI system for financial analysis and earnings research. All development must adhere to these conventions. Also see `.github/copilot-instructions.md` for Copilot-specific guidance and `docs/` for runbooks.

---

## Architecture & Core Concepts

### The Graph
- **Orchestration**: LangGraph StateGraph with nodes = agents, edges = handoffs
- **Topology**: Supervisor routes to workers (researcher, analyst, coder), critic evaluates, feedback loops back
- **State**: `src/orchestration/state.py` defines shared schema (messages, scratchpad, routing, budgets)
- **Persistence**: PostgreSQL checkpoints via `src/orchestration/checkpoints.py`; enables resumption and human-in-the-loop pauses

### Agent Roles
- **Supervisor**: Routes tasks to researcher, analyst, or coder; decides when to finish
- **Researcher**: Web search + RAG retrieval for earnings data
- **Analyst**: Financial analysis, pattern recognition, numerical reasoning
- **Coder**: Code execution in sandbox (Docker/subprocess with limits)
- **Critic**: Evaluates agent output; returns pass/fail + feedback

### Tools & Skills Boundary
- **Tools** (`src/tools/`): Atomic callables with Anthropic schema; schemas in `src/tools/schemas.py`
- **Skills** (`skills/`): Multi-step workflows with bundled instructions + assets; agents load dynamically
- **MCP**: External tool servers exposed via `src/mcp/client.py`

### RAG Pipeline
- **Ingest** (`src/rag/ingest.py`): Load → structure-aware chunk → embed → upsert (idempotent, resumable)
- **Retrieval** (`src/rag/retriever.py`): Hybrid search + rerank + token-budgeted context assembly
- **VectorDB**: pgvector or Qdrant behind `src/rag/vectorstore.py` Protocol; swap cleanly

---

## Code Style & Typing

### Python
- **All files**: Python 3.11+, async-first, strict typing (`from __future__ import annotations`)
- **Functions**: Type-annotated arguments and returns; use `Pydantic` for complex inputs/outputs
- **Async**: Prefer `async def` + `await`; avoid blocking I/O in agent context
- **Error handling**: Typed exceptions (`class ToolError(Exception)`); catch and wrap, don't swallow
- **Imports**: Use `src/` as root (configured in `pyproject.toml`); organize: stdlib → third-party → local

### Naming
- **Agents**: `{role}_agent.py` (e.g., `researcher_agent.py`)
- **Tools**: `{capability}.py` (e.g., `web_search.py`)
- **Skills**: `{skill_domain}/SKILL.md` + `{skill_domain}/scripts/`, `{skill_domain}/resources/`
- **Prompts**: `prompts/{role}/v{N}.md` (immutable; version in `prompts/registry.yaml`)

### Linting & Format
- **Ruff**: `check` + `format`; configured in `pyproject.toml`
- **MyPy**: Strict mode; see `pyproject.toml`
- **Pre-commit**: Runs ruff + mypy + gitleaks on every commit (`.pre-commit-config.yaml`)
- **CI/CD**: `make lint` runs checks; push only after passing

---

## Configuration

### Secrets & Env
- **No hardcoded secrets**; use `pydantic-settings` in `src/config/settings.py`
- **`settings.py`**: Typed env loader + validation at startup
- **`models.py`**: MODEL REGISTRY (logical name → pinned model ID + role routing); update here, not in code
- **`.env`**: git-ignored; copy from `.env.example` (which documents every var with safe defaults)

### Logging
- **Structured logs** via `structlog` (JSON output) in `src/config/logging.py`
- **Context propagation**: Request ID + trace ID in every log line
- **No print()**; use `logger` from `src/config/logging.py`

---

## Project Structure

```
src/agentic_app/
├── main.py                # CLI entry (Typer): `agentic run`, `agentic ingest`, `agentic eval`
├── api/                   # FastAPI surface (if serving as service)
├── config/                # settings.py, models.py (MODEL REGISTRY), logging.py
├── agents/                # Agent definitions: supervisor, researcher, analyst, coder, critic
├── orchestration/         # graph.py, state.py, router.py, checkpoints.py
├── tools/                 # registry.py, schemas.py, web_search.py, code_exec.py, file_io.py, etc.
├── rag/                   # ingest.py, chunking.py, embeddings.py, vectorstore.py, retriever.py
├── memory/                # short_term.py, long_term.py, store.py (working + persistent memory)
├── mcp/                   # client.py, servers.py (Model Context Protocol)
├── llm/                   # anthropic_client.py (ONLY place talking to Anthropic), caching.py, retry.py
├── prompts/               # loader.py (resolves role → active version from prompts/registry.yaml)
└── observability/         # tracing.py, callbacks.py, metrics.py (LangSmith, OpenTelemetry)

prompts/                   # Versioned system prompts (immutable once shipped)
├── registry.yaml          # Maps role → ACTIVE version + metadata
├── shared/                # Reusable fragments: safety.md, output_formats.md, tool_use_policy.md
├── supervisor/, researcher/, analyst/, coder/, critic/
│   └── v1.md, v2.md, ... (each version is immutable)

skills/                    # Agent runtime skills (on-demand workflows)
├── README.md              # Explains SKILL.md convention + agent loading
├── web_research/SKILL.md, code_execution/SKILL.md, ...

evals/                     # First-class eval harness
├── datasets/              # Versioned JSONL: inputs + expected outcomes
├── scorers/               # llm_judge.py, trajectory.py (scoring functions)
├── suites/                # Suite definitions: dataset → agent → scorer → threshold
└── run.py                 # Eval runner (used by eval.yml CI gate)

tests/
├── conftest.py            # Shared fixtures: fake Anthropic client, in-memory store
├── unit/                  # NO network, NO LLM calls, mocked everything
├── integration/           # Real graph wiring with vcr-style recorded LLM responses
```

---

## Build & Test

### Local Development
```bash
# Install (one-time)
make install

# Lint + type-check
make lint

# Run unit + integration tests
make test

# Run eval suite (agent validation gate)
make eval

# Start the app (CLI or API)
make run
```

See `Makefile` for all targets; `make help` lists them.

### Docker
```bash
# Build image
docker build -t earnings-edge:latest .

# Run local stack (app + vectorstore + Postgres + OTel)
docker-compose up
```

### CI/CD Gates
- **`ci.yml`**: Lint + type-check + unit/integration tests on every PR
- **`eval.yml`**: AGENT EVAL GATE — runs eval suite, fails on score regression vs. main (production-distinguishing)
- **`prompt-diff.yml`**: Detects changes under `prompts/` and forces eval run + human review
- **`release.yml`**: Build + push image, tag, changelog

---

## Prompts & Versioning

### The Registry
- **`prompts/registry.yaml`**: Source of truth for which prompt versions are active per role
- **Immutable versioning**: Once `v1.md` is shipped, never edit it; bump to `v2.md` for changes
- **Author + eval score**: Stored in registry metadata so you can track which version won
- **Format**: Fragments composed via `src/prompts/loader.py`; includes shared guardrails + role-specific logic

### Prompt Development
1. Draft in `docs/prompt-templates/` (experiments)
2. Version into `prompts/{role}/vN.md` (immutable)
3. Update `prompts/registry.yaml` to activate
4. Push → triggers `prompt-diff.yml` → eval gate → human review

---

## Tools & Tool Use

### Defining a Tool
1. Create `src/tools/{capability}.py` with a function decorated `@tool_registry.register()`
2. Define schema in `src/tools/schemas.py` as Pydantic model
3. Tool is auto-collected; `registry.py` exports Anthropic-format schemas
4. **Test**: Unit test in `tests/unit/test_tools/`; no side effects in tests

### Handling Tool Errors
- Tool wraps errors in `ToolError(category, message, details)`
- Agent logs the error in the message history for LLM visibility
- Critic reviews whether the agent should retry or escalate
- **Never swallow errors**; always propagate context

---

## Testing & Evaluation

### Unit Tests
- **Location**: `tests/unit/`
- **Constraints**: NO network, NO LLM calls, NO side effects
- **Fixtures**: Fake Anthropic client, in-memory store, frozen clock in `conftest.py`
- **Run**: `make test` or `pytest tests/unit/`

### Integration Tests
- **Location**: `tests/integration/`
- **Setup**: Real graph wiring with vcr-style recorded LLM responses (deterministic replay)
- **Run**: `make test` (both unit + integration) or `pytest tests/integration/`

### Eval Suites
- **Location**: `evals/`
- **Datasets**: Versioned JSONL in `evals/datasets/` (inputs + expected outcomes/rubrics)
- **Scorers**: Scoring functions in `evals/scorers/` (exact-match, LLM-as-judge, trajectory)
- **Suites**: Bind datasets → agents → scorers → pass/fail thresholds in `evals/suites/`
- **Run**: `make eval` (locally) or triggered by `eval.yml` on PR
- **Regression gate**: If score < threshold, PR fails; fix prompt or accept regression with justification

---

## Key Gotchas & Patterns

### Agent Loops
- **Budget counters** in graph state prevent infinite loops; supervisor checks at each step
- **Window + compaction**: Short-term memory truncates to token budget; long-term persists facts
- **Timeout**: Set reasonable limits on total steps + wall-clock time
- **Runbook**: See `docs/runbooks/agent-stuck-in-loop.md`

### Prompt Rollback
- **Active version** in `prompts/registry.yaml` points to the live v{N}.md
- **Fast rollback**: Edit registry to point to previous version; no code redeploy
- **Runbook**: See `docs/runbooks/rollback-a-prompt.md`

### Rate Limits
- **Backoff**: Exponential retry logic in `src/llm/retry.py` handles RateLimitError
- **Circuit breaker**: After N failures, fast-fail; don't hammer the API
- **Monitoring**: Prometheus metrics in `src/observability/metrics.py` track token usage + cost

### Tracing & Debugging
- **LangSmith**: Traces all agent runs; correlate with Prometheus metrics
- **OpenTelemetry**: `src/observability/tracing.py` + OTel collector in docker-compose
- **Replay**: `scripts/replay_trace.py` re-runs a captured production trace locally
- **Time-travel debugging**: PostgreSQL checkpoints allow resuming from past states

### Large Outputs
- **Token budgets**: Every component (retriever, short-term memory, tools) has token limits
- **Chunking**: RAG pipeline uses structure-aware chunking for readability
- **Streaming**: FastAPI `/chat` endpoint streams via Server-Sent Events (SSE)

---

## Observability

- **Logs**: Structured JSON via `structlog`; see `src/config/logging.py`
- **Traces**: LangSmith + OpenTelemetry; @traced decorator in `src/observability/tracing.py`
- **Metrics**: Prometheus in `src/observability/metrics.py` (tokens, latency, tool calls, eval scores)
- **Stack**: Postgres (checkpoints), vector DB (pgvector/Qdrant), OTel collector, Prometheus scrape

---

## Common Agent Tasks

| Task | Command | Notes |
|------|---------|-------|
| Add a new worker agent | Create `src/agents/{role}_agent.py`; inherit `BaseAgent`; test in `tests/` | Update supervisor router |
| Add a tool | Create `src/tools/{capability}.py`; define schema in `schemas.py`; register via decorator | Auto-collected |
| Update a prompt | Draft in `docs/prompt-templates/`; version into `prompts/{role}/vN.md`; update `registry.yaml` | Triggers eval gate |
| Fix a failing eval | Debug locally with `scripts/replay_trace.py`; update agent/tool logic; re-run `make eval` | Commit eval score improvement |
| Deploy | Push to main; CI/CD runs lint + tests + eval; merge if green; `release.yml` builds + pushes image | Check CODEOWNERS for prompt changes |

---

## Links

- **Architecture**: `docs/architecture.md`
- **ADRs**: `docs/adr/` (immutable decisions)
- **Runbooks**: `docs/runbooks/` (on-call playbooks)
- **Tests**: `tests/README.md`
- **Evals**: `evals/README.md`
