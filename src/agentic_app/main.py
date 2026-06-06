"""CLI entrypoint for the earnings-edge application."""

from __future__ import annotations

import typer

app = typer.Typer()


@app.command()
def run() -> None:
    """Start the agentic app."""
    typer.echo("Starting earnings-edge agent...")


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
