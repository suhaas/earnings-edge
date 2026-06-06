# earnings-edge: Project Memory for Claude Code

This document is loaded at session start and contains architecture, commands, conventions, verification loops, and gotchas.

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

## Build & Test Commands

```bash
# Install
make install

# Lint + type-check
make lint

# Run unit + integration tests
make test

# Run eval suite (agent validation gate)
make eval

# Start the app (CLI or API)
make run

# Full trace (debugging)
make trace
```

---

## Verification Loop (Claude Code Workflow)

1. **Code change**: Edit file → auto-save triggers format-on-save
2. **Local validation**: `make lint` (ruff + mypy) before pushing
3. **Test locally**: `make test` (unit + integration)
4. **Eval gate**: `make eval` to validate against baseline
5. **Push**: Triggers CI/CD (ci.yml → eval.yml → release.yml)
6. **Human review**: Check CODEOWNERS for prompt changes

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

## Project Structure at a Glance

```
src/agentic_app/        # Python package
prompts/                # Versioned system prompts (immutable)
skills/                 # Agent runtime skills + workflows
evals/                  # Evaluation datasets, scorers, suites
tests/                  # Unit + integration tests
docs/                   # Architecture, ADRs, runbooks
scripts/                # One-off operational utilities
.github/                # GitHub + Copilot configuration
.claude/                # Claude Code dev harness
.vscode/                # VS Code workspace settings
.devcontainer/          # Reproducible dev environment
```

---

## Links

- **Full guide**: `.github/copilot-instructions.md` (Copilot-centric) or `AGENTS.md` (agent-centric)
- **Architecture**: `docs/architecture.md`
- **ADRs**: `docs/adr/` (immutable decisions)
- **Runbooks**: `docs/runbooks/` (on-call playbooks)
- **Tests**: `tests/README.md`
- **Evals**: `evals/README.md`
