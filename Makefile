.PHONY: help install lint format test eval run trace clean

help:
	@echo "earnings-edge project targets:"
	@echo ""
	@echo "  make install       Install dependencies (uv)"
	@echo "  make lint          Check code style + type hints (ruff + mypy)"
	@echo "  make format        Auto-format code (ruff)"
	@echo "  make test          Run unit + integration tests (pytest)"
	@echo "  make eval          Run eval suite (validates agents vs. baseline)"
	@echo "  make run           Start the application (CLI or API)"
	@echo "  make trace         Run with LangSmith + OpenTelemetry tracing"
	@echo "  make clean         Remove build artifacts and caches"
	@echo ""

install:
	uv sync --all-extras

lint:
	ruff check src tests
	mypy src

format:
	ruff format src tests
	ruff check --fix src tests

test:
	pytest tests/ -v

eval:
	python evals/run.py

run:
	python -m agentic_app.main

trace:
	LANGSMITH_TRACING=true OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 python -m agentic_app.main

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name .coverage -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type d -name dist -exec rm -rf {} +
	find . -type d -name build -exec rm -rf {} +
	find . -type d -name *.egg-info -exec rm -rf {} +
