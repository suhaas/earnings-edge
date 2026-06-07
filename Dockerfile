# Multi-stage Dockerfile for earnings-edge

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./

# Build dependencies
RUN uv export --frozen > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy pip requirements from builder
COPY --from=builder /build/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY skills/ ./skills/

# Make the src/ layout importable as the `agentic_app` package (no pip install of the
# project itself in this image, so the package dir must be on PYTHONPATH).
ENV PYTHONPATH=/app/src

# No HEALTHCHECK: this container runs the CLI as a one-shot batch job, not an HTTP
# server, so there is nothing on :8000 to probe. If you switch the CMD below to serve
# the FastAPI app (`uvicorn agentic_app.api.app:app --host 0.0.0.0 --port 8000`),
# restore a healthcheck such as:
#   HEALTHCHECK CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# If the image build fails with certificate errors, it's the same TLS-interception proxy —
# the in-container pip install is hitting it. You'd need to inject your proxy's root CA into
# the build (out of scope here; the native path avoids this via UV_SYSTEM_CERTS).

# Run the application (the `run` subcommand; override args via docker-compose `command:`)
CMD ["python", "-m", "agentic_app.main", "run"]
