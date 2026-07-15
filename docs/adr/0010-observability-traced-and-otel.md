# ADR-0010: Observability — `@traced` + OTel Bootstrap; Metrics Deferred

**Status**: Accepted
**Date**: 2026-07-15

## Context

`src/agentic_app/observability/` is the most precisely specified stub in the repo. The docs name the
exact missing API.

`AGENTS.md:294-296`:

> *(No `observability/` module yet — it is an empty stub, so there are no Prometheus metrics and
> **no `@traced` decorator** despite the env vars.)*

`AGENTS.md:316-321` names the metrics:

> **Metrics** *(planned)*: Prometheus counters for **tokens, latency, tool calls, eval scores**

**An entire pipeline is provisioned with zero producers** — the strongest circumstantial signal in
the repo:

- `pyproject.toml` declares `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`,
  and `langsmith`. **None is imported anywhere.**
- `docker-compose.yml` runs an `otel-collector` (4317 gRPC / 4318 HTTP / 8888 Prometheus) **and** a
  full `prometheus` service (9090).
- `otel-collector-config.yaml` and `prometheus.yml` both exist on disk.
- `Makefile`'s `trace` target already exports `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`.
- `.devcontainer` forwards 8888 labelled "Prometheus".

So the collector listens on 4317 and receives nothing; Prometheus scrapes the collector and gets
nothing. **`OTEL_EXPORTER_OTLP_ENDPOINT` is completely inert.**

**An important nuance the docs get right.** Tracing **partly works today without this module**:
`LANGSMITH_TRACING=true` is read by the LangChain/LangGraph SDK itself, so `make trace` produces real
LangSmith traces. That is why `docs/architecture.md:54-55` says *"partial"*, not *"not implemented"*.
Only the **OTel leg** is missing.

**Two of the four intended metrics have no source.** ADR-0008 deletes the in-repo tool layer, so
"tool calls" is unmeasurable in-process. `evals/run.py` has `PLACEHOLDER = True` and emits
`"current_score": None`, so "eval scores" has nothing to report.

**`prometheus.yml` is broken independently of any of this.** Line 11 targets `localhost:8888` — but
inside the Prometheus container, `localhost` is *Prometheus itself*, not the collector. It must be
`otel-collector:8888`. The scrape has never worked.

## Decision

1. **Build `observability/tracing.py`**: an `init_tracing()` OTel bootstrap (TracerProvider +
   OTLPSpanExporter) and the **`@traced` decorator** the docs already name. Both **env-gated** on
   `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT`, and a **no-op when unset** — no import of the OTel
   SDK, no overhead.
2. **Defer `observability/metrics.py`.** Land it only after ADR-0008 settles the tool layer and the
   eval suite emits real scores. Shipping two of four counters invites a half-instrumented dashboard
   that looks complete.
3. **Fix `prometheus.yml`** (`localhost:8888` → `otel-collector:8888`) regardless — it is a
   standalone bug.
4. **Keep the logs leg where it is.** `config/logging.py`'s structlog setup is the logs answer; do
   not duplicate it under `observability/`. (It currently has zero importers — a separate problem.)

**`@traced` must never be applied in `graph.py`.** `tests/integration/test_trajectory.py` re-imports
`graph.py` against faked agent modules; a new top-level import there executes for real. Decorate
inside agent modules (which are faked away) or at the `main`/`checkpoint` boundary.

## Rationale

- **The API is already named.** `@traced` is not a design choice — it is written down in three docs.
  Building anything else would create a fourth thing to reconcile.
- **Env-gated no-op** keeps the hermetic test suite and local runs free of OTel entirely, and matches
  how `LANGSMITH_TRACING` already behaves.
- **Deferring metrics is honest.** Two of four counters would be permanently zero. A dashboard with
  two dead panels is worse than no dashboard.
- **Fix the scrape now** because it is cheap, independent, and would otherwise make the eventual
  metrics work look broken for an unrelated reason.

## Alternatives Considered

- **Build metrics now with the two measurable counters** (tokens, latency): rejected — "tool calls"
  and "eval scores" would read as zero rather than absent, which is actively misleading.
- **Auto-instrumentation** (`opentelemetry-instrumentation-*`): rejected — not declared, adds
  dependencies, and instruments HTTP/DB rather than the agent-step boundary we actually care about.
- **Drop OTel and keep LangSmith only**: tempting — LangSmith already works and OTel currently
  exports traces to a `logging` exporter that just prints to collector stdout. Rejected because the
  infrastructure is already paid for and the docs promise it. But see Consequences: **traces
  currently go nowhere useful**, and that must be fixed for the module to be worth anything.
- **Put `@traced` in `graph.py` around each node**: rejected — breaks the hermetic trajectory test.

## Consequences

- **Requires `prometheus-client`** — a new dependency — when metrics land, **plus** a `pyproject`
  `[[tool.mypy.overrides]]` entry, because `ignore_missing_imports = false` globally.
- **`otel-collector-config.yaml` sends traces only to the `logging` exporter.** They are debug-printed
  to collector stdout and vanish. A real trace backend (Jaeger/Tempo) is needed for `@traced` to be
  useful beyond `make trace`. Also: the `logging` exporter is **deprecated** in current collector
  releases (replaced by `debug`), and the image is `:latest` — this config may already warn.
- "Tool calls" is **permanently unmeasurable in-process** after ADR-0008. If it is ever wanted, it
  must come from Composio.
- `docs/runbooks/agent-stuck-in-loop.md` tells operators to "check the trace" and run
  `scripts/replay_trace.py` — a placeholder that prints one line. The runbook stays fiction until
  this module and a trace backend exist.
- `config/logging.py` has zero importers, so there is **no structured logging today** despite
  `CLAUDE.md`'s "No print(); use logger". Fixing that is separate but related — the logs leg of the
  same three-part story.
