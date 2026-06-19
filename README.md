# earnings-edge

A multi-agent AI system that turns a company's quarterly earnings into a concise,
source-attributed analyst brief.

## Overview

**earnings-edge** runs a small team of specialized agents over
[LangGraph](https://langchain-ai.github.io/langgraph/) to analyze one ticker/quarter end to
end: it pulls the earnings transcript and SEC filing, scores management tone with a local
FinBERT model, extracts KPIs and compares them to analyst consensus, fuses everything into a
transparent **SurpriseSignal**, writes a Markdown brief, grounding-checks it for
hallucinations, and (optionally) emails it.

```bash
uv run python -m agentic_app.main run --ticker AAPL --year 2025 --quarter 1
```

👉 **See a real generated brief:** [examples/AAPL-Q1-FY2025-brief.md](examples/AAPL-Q1-FY2025-brief.md)

### Key features

- **Multi-agent pipeline** on LangGraph — ingestion → sentiment + KPI → synthesis → evaluation → delivery
- **Local sentiment** — FinBERT (`ProsusAI/finbert`) tone + hedging/certainty; runs on CPU, no API key
- **Grounded synthesis** — every number is attributed to a KPI/sentiment fact, with an
  LLM-as-judge **faithfulness gate** and a self-correction (revise) loop
- **Transparent signal** — a weighted, explainable `SurpriseSignal` (score, direction, confidence)
- **Durable checkpoints** — resume runs via SQLite (default) or PostgreSQL
- **Multi-channel delivery** — ship the brief to Gmail / Slack / Notion / Sheets via Composio
- **Versioned prompts** — immutable prompt versions in a registry, gated by tests + CI

## How it works

```text
                  ┌─────────────┐
   ticker/qtr ───▶│  ingestion  │   EarningsCall transcript + SEC 8-K (split prepared vs Q&A)
                  └──────┬──────┘
               ┌─────────┴─────────┐              (parallel fan-out)
         ┌─────▼─────┐       ┌─────▼─────┐
         │ sentiment │       │    kpi    │   FinBERT tone  /  Claude extraction + yfinance consensus
         └─────┬─────┘       └─────┬─────┘
               └─────────┬─────────┘              (fan-in)
                  ┌──────▼──────┐
                  │  synthesize │   Claude → SurpriseSignal + Markdown brief
                  └──────┬──────┘
                  ┌──────▼──────┐    grounding < 0.8 ─┐
                  │  evaluate   │   faithfulness judge │  (revise loop, budget = 2)
                  └──────┬──────┘◀────────────────────┘
                  ┌──────▼──────┐
                  │   deliver   │   email / Slack / Notion via Composio
                  └──────┬──────┘
                       ( END ) ──▶  prints GROUNDING / SIGNAL / DELIVERY + the brief
```

Each node is an agent; a shared typed state (transcript, sentiment, KPIs, signal, brief)
flows between them. See [docs/architecture.md](docs/architecture.md) and [AGENTS.md](AGENTS.md)
for the full design.

## Setup

**Prerequisites:** Python 3.11+, [`uv`](https://docs.astral.sh/uv/), git. (Docker only for the
optional Postgres / observability stack.)

```bash
git clone <repo> && cd earnings-edge
uv sync --all-extras          # creates .venv and installs everything
cp .env.example .env          # then fill in the keys below
```

**Keys (edit `.env`):**

| Variable | Required? | What it's for |
|---|---|---|
| `ANTHROPIC_API_KEY` | **yes** | Claude calls (KPI, synthesis, evaluation). Get one at [console.anthropic.com](https://console.anthropic.com/) — separate from a Claude Pro/Max plan. |
| `EDGAR_IDENTITY` | **yes** | SEC User-Agent string, e.g. `Jane Analyst jane@example.com`. |
| `COMPOSIO_API_KEY` + `COMPOSIO_USER_ID` | for delivery | Email/Slack/etc. delivery. The key needs **write** scope; connect Gmail once (see below). |
| `EARNINGSCALL_API_KEY` | optional | Blank = AAPL/MSFT transcripts only. |

> **First run downloads FinBERT** (~440 MB, `ProsusAI/finbert`) to your HuggingFace cache —
> one time, then it runs offline. The app uses your OS certificate store (`truststore`) so it
> works behind a TLS-inspecting proxy; after the first download, set `HF_HUB_OFFLINE=1` in
> `.env` to skip network revalidation.

Validate your keys without spending a full run:

```bash
uv run python scripts/check_anthropic_key.py     # -> OK: API key works
uv run python scripts/check_composio_key.py      # -> OK + a Gmail "connect" URL (if delivering)
```

## Run

```bash
uv run python -m agentic_app.main run --ticker AAPL --year 2025 --quarter 1
```

- Use a **reported** quarter for AAPL/MSFT (free tier); other tickers need `EARNINGSCALL_API_KEY`.
- Checkpoints default to a local SQLite file (`earningsedge.db`, git-ignored). Set
  `DATABASE_URL=postgres://…` (and `docker compose up -d postgres`) for the durable Postgres
  backend, or pick the **"Python: Main (Postgres)"** VS Code launch config.

## Expected output

A successful run prints a one-line summary, then the full Markdown brief:

```text
[checkpoint] local SQLite + in-memory store (non-durable)
GROUNDING: 0.86
SIGNAL: 25.5 bullish
DELIVERY: ['...emailed / posted to #earnings ...']

# Apple Inc. (AAPL) Q1 FY2025 Earnings Brief
## TL;DR
...
## Beat/Miss   ## Tone & Hedging   ## Guidance   ## Risks   ## Sources
```

- **`GROUNDING`** — faithfulness score in `[0, 1]` from the evaluation judge.
- **`SIGNAL`** — the SurpriseSignal score + direction (`bullish` / `bearish` / `neutral`).
- **`DELIVERY`** — per-channel status; a delivery error here is **non-fatal** (the brief still prints).
- **Brief** — a ≤400-word, fully source-attributed analyst note (every figure cites a KPI/sentiment field).

📄 Full worked example: **[examples/AAPL-Q1-FY2025-brief.md](examples/AAPL-Q1-FY2025-brief.md)**

## Project Structure

See [AGENTS.md](AGENTS.md) or [.github/copilot-instructions.md](.github/copilot-instructions.md) for the complete project structure and conventions.

### Key Directories
- **`src/agentic_app/`** — Python application package (agents, orchestration, prompts loader)
- **`prompts/`** — Versioned system prompts (organized by role)
- **`skills/`** — Agent runtime skills and workflows
- **`evals/`** — Evaluation datasets, scorers, and suites
- **`examples/`** — Sample generated output
- **`scripts/`** — Operational utilities (key checks, eval gate)
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

> No `make` on Windows? Every target is a thin wrapper — run the underlying command, e.g.
> `uv run ruff check src tests && uv run mypy src` (lint) or `uv run pytest tests/` (test).

## Common Commands

| Command | Purpose |
|---------|---------|
| `make install` | Install dependencies (`uv sync --all-extras`) |
| `make lint` | Check code style + types (ruff + mypy) |
| `make test` | Run unit + integration tests (pytest) |
| `make eval` | Run eval suite (agent validation) |
| `make run` | Run the pipeline (CLI) |
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
- Prompt changes must run the eval gate (the `eval-gate` job in `ci.yml`)
- Evals must not regress vs. main branch
- CODEOWNERS required for prompts/ and agents/

## License

[Add your license here]
