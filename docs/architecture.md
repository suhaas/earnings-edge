# earnings-edge Architecture

## System Overview

earnings-edge is a multi-agent system orchestrated via LangGraph. It is a **fixed pipeline**, not a
supervisor/router topology — every edge is declared explicitly in
`src/agentic_app/orchestration/graph.py`.

```text
CLI: python -m agentic_app.main run --ticker NVDA --year 2025 --quarter 4
    ↓
Ingestion  (transcript / press-release text)
    ↓
    ├→ Sentiment  (tone analysis)      ─┐  parallel fan-out
    └→ KPI        (structured extract) ─┘
    ↓  fan-in: waits for BOTH
Synthesis  (fuses into signal + brief_markdown)
    ↓
Evaluation (grounding score) ──route_after_eval──→ Revise ──┐
    ↓                                                 ↑      │
    │                                                 └──────┘  self-correction loop
    ↓
Delivery → END
```

## Graph Topology

- **Nodes**: `ingest`, `sentiment`, `kpi`, `synthesize`, `revise`, `evaluate`, `deliver`
- **Edges**: static fan-out/fan-in; the only conditional edge is `route_after_eval`
  (`evaluate` → `revise` | `deliver`)
- **State** (`src/agentic_app/orchestration/state.py`): `EarningsState` TypedDict —
  ticker/year/quarter, transcripts, `sentiment` + `kpis` (`Annotated[..., operator.add]` so the
  parallel branches merge), `signal`, `brief_markdown`, `grounding_score`, `revision_count`,
  `delivery_log`, `errors`. Pydantic models `EarningsKPIs` + `SurpriseSignal` live here too.
- **Loop bound**: `revision_count`, bumped by the `revise` wrapper (`_bump_and_synth`)
- **Persistence**: selected in `main.py` from `DATABASE_URL` — a `postgres` URL uses
  `PostgresSaver` + `PostgresStore`; anything else uses `SqliteSaver` (`earningsedge.db`) +
  `InMemoryStore`. Unreachable Postgres falls back to SQLite with a warning.
  `thread_id` = `f"{ticker}-{year}-Q{quarter}"`; checkpoints chain via `parent_checkpoint_id`
  (resume, time-travel debugging).

## Key Components

- **Tools** (`src/agentic_app/tools/`): `registry.py` (`ToolRegistry`) + Pydantic `schemas.py`
- **Skills** (`skills/`): domain workflows — `kpi-extraction`, `finbert-tone-analysis`,
  `sec-edgar-8k-retrieval`, `signal-synthesis-scoring`, `grounding-faithfulness-eval`,
  `composio-delivery`, and others
- **Prompts**: `prompts/{role}/v{N}.md`, immutable; active version resolved by
  `src/agentic_app/prompts/loader.py` from `prompts/registry.yaml`
- **Evaluation**: versioned datasets (`evals/datasets/`) + scorers (`llm_judge.py`,
  `trajectory.py`) + `evals/suites/regression.yaml` gate
- **RAG** *(planned — not implemented)*: `src/agentic_app/rag/` is a stub. Intended:
  ingest → chunk → embed → hybrid retrieve + rerank behind a pgvector/Qdrant Protocol.
- **Observability** *(partial)*: LangSmith + OTel are env-gated (`make trace`); the OTel collector
  runs in docker-compose. There is no in-repo `observability/` module and no Prometheus metrics yet.

## Deployment

- **Local**: `docker-compose up` (app + Postgres + Qdrant + OTel)
- **Production**: Docker image deployed to container registry
- **CI/CD**: GitHub Actions (lint → test → eval gate), plus `prompt-diff.yml` and `release.yml`
