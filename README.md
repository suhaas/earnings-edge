# earnings-edge

A multi-agent AI system for financial analysis and earnings research.

## Overview

**earnings-edge** uses LangGraph to orchestrate a team of specialized AI agents (researcher, analyst, coder, critic) that work together to extract insights from earnings data, financial reports, and market commentary.

### Key Features

- **Multi-agent orchestration**: Supervisor routes tasks to specialized workers
- **RAG pipeline**: Ingest → chunk → embed → hybrid retrieve + rerank
- **Durable checkpoints**: Resume long-running analyses from saved states
- **Eval-driven development**: Regression-detected CI gate for agent quality
- **Sandboxed code execution**: Agents can run Python, SQL, and analysis scripts safely
- **Structured logging**: JSON logs with trace context for debugging
- **Prompt versioning**: Immutable prompt versions with registry-based activation

## Quick Start

### Prerequisites
- Python 3.11+
- `uv` for dependency management
- Docker + Docker Compose (for local stack)
- Claude API key (for agent LLM)

### Setup

```bash
# Clone and install
git clone <repo>
cd earnings-edge
make install

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run linting + type checks
make lint

# Run tests
make test

# Run eval suite
make eval
```

### Local Development

```bash
# Start the application
make run

# Run with tracing (LangSmith + OpenTelemetry)
make trace

# Full local stack (app + Postgres + vector DB + OTel)
docker-compose up
```

> **Checkpoints:** by default `run` uses a local SQLite file + in-memory store
> (prints `[checkpoint] local SQLite + in-memory store (non-durable)`). Set
> `DATABASE_URL=postgres://…` (and `docker compose up -d postgres`) to switch to the
> durable Postgres backend — or pick the **"Python: Main (Postgres)"** VS Code launch
> config. If Postgres is unreachable, it falls back to SQLite with a warning.

## Project Structure

See [AGENTS.md](AGENTS.md) or [.github/copilot-instructions.md](.github/copilot-instructions.md) for the complete project structure and conventions.

### Key Directories
- **`src/agentic_app/`** — Python application package
- **`prompts/`** — Versioned system prompts (organized by role)
- **`skills/`** — Agent runtime skills and workflows
- **`evals/`** — Evaluation datasets, scorers, and suites
- **`tests/`** — Unit and integration tests
- **`docs/`** — Architecture, ADRs, and runbooks
- **`.github/`** — GitHub Actions CI/CD and Copilot configuration
- **`.claude/`** — Claude Code dev harness (custom commands, skills)
- **`.vscode/`** — VS Code workspace settings

## Development Workflow

1. **Write code** in `src/agentic_app/` following Python guidelines (see [.github/instructions/python.instructions.md](.github/instructions/python.instructions.md))
2. **Lint locally** — `make lint` enforces ruff + mypy
3. **Test locally** — `make test` (unit + integration)
4. **Eval locally** — `make eval` (validate against baseline)
5. **Push** → CI/CD gates run automatically
6. **Prompt changes** trigger eval comparison + human review

## Common Commands

| Command | Purpose |
|---------|---------|
| `make install` | Install dependencies |
| `make lint` | Check code style + types |
| `make test` | Run unit + integration tests |
| `make eval` | Run eval suite (agent validation) |
| `make run` | Start CLI or API |
| `make trace` | Run with LangSmith + OpenTelemetry |
| `make help` | List all make targets |

## Documentation

- **[AGENTS.md](AGENTS.md)** or **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Full architecture and conventions
- **[CLAUDE.md](CLAUDE.md)** — Project memory for Claude Code
- **[docs/architecture.md](docs/architecture.md)** — System overview and diagrams
- **[docs/adr/](docs/adr/)** — Architecture Decision Records
- **[docs/runbooks/](docs/runbooks/)** — On-call playbooks

## Contributing

See [.github/pull_request_template.md](.github/pull_request_template.md) for PR checklist.

Key points:
- All code must pass `make lint` and `make test`
- Prompt changes must run eval gate (eval.yml)
- Evals must not regress vs. main branch
- CODEOWNERS required for prompts/ and agents/

## License

[Add your license here]
