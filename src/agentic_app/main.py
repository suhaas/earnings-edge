"""CLI entrypoint for the earnings-edge application."""

from __future__ import annotations

import io
import sys

import truststore
import typer
from dotenv import load_dotenv

# Force UTF-8 console output so LLM-generated briefs (em-dashes, smart quotes, bullets,
# currency/percent symbols) and any Unicode print cleanly on Windows' legacy cp1252
# console instead of raising UnicodeEncodeError mid-output.
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Load .env at IMPORT time — before any command imports the graph, which pulls in
# transformers/huggingface_hub. Those read env-driven settings (e.g. HF_HUB_OFFLINE)
# at *their* import time, so the values must already be in os.environ here.
load_dotenv()

# Route all outbound HTTPS (httpx/requests: Anthropic, yfinance, SEC, Composio, ...)
# through the OS certificate store so the app works behind a TLS-inspecting proxy/AV.
# Must run before any TLS client is constructed.
truststore.inject_into_ssl()

app = typer.Typer()


@app.command()
def run(ticker: str = "NVDA", year: int = 2025, quarter: int = 4) -> None:
    """Run the earnings-edge graph for one ticker/quarter.

    The checkpoint + store backend is chosen by DATABASE_URL: a ``postgres...`` URL uses
    the durable PostgresSaver + PostgresStore (the docker-compose ``postgres`` service);
    anything else uses a local SQLite file + in-memory store. If a postgres URL is set
    but unreachable, it falls back to SQLite with a warning so local runs never hard-fail.
    """
    import os
    from contextlib import ExitStack
    from typing import Any

    from dotenv import load_dotenv

    from agentic_app.orchestration.graph import build_graph

    load_dotenv()
    db_url = os.environ.get("DATABASE_URL", "").strip()

    checkpointer: Any
    store: Any
    with ExitStack() as stack:
        if db_url.startswith("postgres"):
            try:
                from langgraph.checkpoint.postgres import PostgresSaver
                from langgraph.store.postgres import PostgresStore

                store = stack.enter_context(PostgresStore.from_conn_string(db_url))
                checkpointer = stack.enter_context(PostgresSaver.from_conn_string(db_url))
                store.setup()  # idempotent: create tables on first run
                checkpointer.setup()
                typer.echo("[checkpoint] durable Postgres backend")
            except Exception as exc:
                typer.echo(
                    f"[checkpoint] Postgres unavailable ({type(exc).__name__}); falling back "
                    "to local SQLite. Start it with: docker compose up -d postgres"
                )
                db_url = ""

        if not db_url.startswith("postgres"):
            from langgraph.checkpoint.sqlite import SqliteSaver
            from langgraph.store.memory import InMemoryStore

            store = InMemoryStore()
            checkpointer = stack.enter_context(SqliteSaver.from_conn_string("earningsedge.db"))
            typer.echo("[checkpoint] local SQLite + in-memory store (non-durable)")

        graph = build_graph(checkpointer=checkpointer, store=store)
        config = {"configurable": {"thread_id": f"{ticker}-{year}-Q{quarter}"}}
        final = graph.invoke(
            {
                "ticker": ticker,
                "year": year,
                "quarter": quarter,
                "user_id": os.environ.get("COMPOSIO_USER_ID", "default"),
                "revision_count": 0,
            },
            config,
        )
        typer.echo(f"GROUNDING: {final.get('grounding_score')}")
        signal = final.get("signal", {})
        typer.echo(f"SIGNAL: {signal.get('score')} {signal.get('direction')}")
        typer.echo(f"DELIVERY: {final.get('delivery_log')}")
        typer.echo("\n" + final.get("brief_markdown", ""))


@app.command()
def ingest() -> None:
    """Ingest data into the RAG system."""
    typer.echo("Ingesting data...")


@app.command()
def eval_suite() -> None:
    """Run the eval suite."""
    typer.echo("Running evals...")


if __name__ == "__main__":
    app()
