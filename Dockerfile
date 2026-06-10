# syntax=docker/dockerfile:1
# Container image for the TradeIQ Sales Assistant — deployable to Azure
# (AKS / Container Apps). Uses uv for reproducible, lockfile-pinned installs.

FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1
WORKDIR /app

# uv binary from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 1) Install runtime dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Install the application package
COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Liveness/readiness probes: GET /livez and /readyz
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
