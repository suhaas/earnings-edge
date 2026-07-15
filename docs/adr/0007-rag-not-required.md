# ADR-0007: RAG Is Not Required by the Domain Design; Delete `rag/`

**Status**: Accepted
**Date**: 2026-07-15

## Context

`src/agentic_app/rag/` is a stub (`__init__.py` only), and it is the **only** empty package with a
real written design. `docs/architecture.md:52-53`:

> **RAG** *(planned — not implemented)*: `src/agentic_app/rag/` is a stub. Intended:
> **ingest → chunk → embed → hybrid retrieve + rerank behind a pgvector/Qdrant Protocol**.

The hyperparameters were pre-chosen in `.env.example`: `all-MiniLM-L6-v2` embeddings, chunk 512 /
overlap 50, top-k 5, `cross-encoder/ms-marco-MiniLM-L-12-v2` reranker. A `vectordb` service runs in
`docker-compose.yml`. `settings.py` **requires** `vectordb_url`. `main.py` even has an empty
`ingest()` CLI command. `.devcontainer` forwards port 6333.

That is a lot of scaffolding. But two facts decide this:

**1. No skill needs it.** All **13** domain skills were read. **Zero** reference embeddings,
chunking, vectorstores, top-k, reranking, or semantic search. The pipeline fetches whole transcripts
by `(ticker, year, quarter)` and passes raw text to Claude: `kpi_agent.py` caps at `[:18000]`,
`evaluation_agent.py` at `[:12000]`. **A single earnings call fits in context.** The one genuine
cross-quarter need — trailing 8-quarter tone — is served by the **Store** (ADR-0005), not a
vectorstore. `sec-edgar-8k-retrieval` is "retrieval" in the API-fetch sense, not the vector sense.

**2. The vectorstore decision was never made, and the artifacts contradict each other.**

| Signal | Points to |
|---|---|
| `docker-compose.yml` active service | **Qdrant** (`qdrant/qdrant:latest`) |
| `VECTORDB_URL=http://localhost:6333` (required by `settings.py`) | **Qdrant** |
| `.devcontainer` forwarded port 6333 | **Qdrant** |
| declared Python dependency | **pgvector** (`pgvector>=0.2.0`) |
| `qdrant-client` | **absent — zero occurrences in `uv.lock`** |

The running service is Qdrant; the installable client is pgvector. **Neither path works as-is.**
There is no decision here to preserve — only an unresolved conflict.

`scripts/seed_vectorstore.py` reveals nothing: it is a 13-line placeholder that prints
`"Seeding vector store with sample data..."`.

## Decision

**RAG is not required by this domain design. Delete it.**

Remove: `src/agentic_app/rag/`, `scripts/seed_vectorstore.py`, the `vectordb` service in
`docker-compose.yml`, the `.env.example` RAG block, `vectordb_url` from `Settings`, and the
`ingest()` CLI stub in `main.py`.

**Revisit when** — and only when — a requirement appears that context-stuffing cannot serve.
Concretely: *multi-quarter or cross-company semantic search* ("find every mention of supply-chain
risk across NVDA's last 8 calls"), or transcripts that stop fitting in context.

**If revisited, prefer pgvector.** We already run Postgres for checkpoints and the store (ADR-0006),
so pgvector adds **zero new infrastructure**, and `pgvector>=0.2.0` is already declared. Qdrant's
head start in `docker-compose` is not worth a second stateful service and a new client dependency.

## Rationale

- **Zero consumers.** Building a retrieval layer no agent calls repeats the exact mistake this
  refactor exists to correct — `model_registry` sat mis-pinned for months precisely because nothing
  called it.
- **The domain design is coherent without it.** 13 skills describe a complete system. That is
  evidence of a *considered* architecture, not an oversight.
- **A conflict is not a decision.** Choosing Qdrant-vs-pgvector now would be inventing intent, not
  recording it.
- **It removes a real bug.** `settings.py` requires `vectordb_url` for a subsystem that does not
  exist — a required field for a service nothing reads.
- **Deleting is reversible; the spec survives in this ADR and in git.**

## Alternatives Considered

- **Build it on Qdrant** (matches compose/env/devcontainer): rejected — needs a new `qdrant-client`
  dependency and a second stateful service, to serve zero callers.
- **Build it on pgvector** (matches the declared dep, reuses Postgres): rejected for now — cheaper
  than Qdrant, but still zero callers. This is the preferred option *if* the trigger fires.
- **Keep the stub, mark it deferred**: rejected — that is today's state, and today's state is what
  let a required-but-unread `vectordb_url` sit in `Settings`. A deferred stub is indistinguishable
  from an unfinished one.
- **Keep `pgvector` + `sentence-transformers` "for later"**: rejected — unused dependencies are
  supply-chain surface and lock churn.

## Consequences

- `settings.py` loses a required field that nothing reads (see the settings wire-or-delete work).
- **Dependency check required before removal.** `sentiment_agent` needs `transformers` for FinBERT,
  which arrives transitively via `sentence-transformers`. Verify the dep graph before dropping
  `sentence-transformers`, or FinBERT breaks. `pgvector` is safe to drop.
- `docs/architecture.md:52-53`, `AGENTS.md`, `CLAUDE.md`, and `.github/copilot-instructions.md` must
  drop their RAG sections in the same change (the maintenance contract at `AGENTS.md:5-8`).
- ADR-0001's "mitigated via adapters" no longer needs a vectorstore `Protocol`.
- If the trigger fires, this ADR is superseded — not reopened. The successor should re-derive the
  design from the requirement, not from `.env.example`'s pre-chosen hyperparameters.
