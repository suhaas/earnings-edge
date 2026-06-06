"""FastAPI application (optional HTTP service)."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="earnings-edge", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
