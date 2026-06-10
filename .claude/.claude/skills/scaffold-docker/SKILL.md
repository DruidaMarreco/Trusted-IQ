---
name: scaffold-docker
description: Use this skill when the user asks to containerize a Python application, create a Dockerfile, docker-compose, or set up healthchecks. Covers Phase 5 of the engineering Quickstart.
---

# Scaffold Docker (Fase 5)

Creates a multi-stage `Dockerfile`, `docker-compose.yml`, `.dockerignore`, and wires `HEALTHCHECK` + health endpoints.

## When to use

- "Containerize the app"
- "Create Dockerfile"
- "docker-compose"
- "Add healthcheck"

## Pre-conditions

- Project is an application (not a pure library).
- `uv.lock` exists and is committed.

## Steps

### 1. `.dockerignore`

```
.git
.venv
__pycache__
*.pyc
.env
.env.*
tests/
docs/
*.md
.github/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage
coverage.xml
```

### 2. Multi-stage `Dockerfile`

```dockerfile
# --- Base ---
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./

# --- Development ---
FROM base AS development
RUN uv sync --group dev --frozen
COPY . .
CMD ["uv", "run", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--reload"]

# --- Production ---
FROM base AS production
RUN uv sync --frozen --no-dev
COPY src/ src/
RUN useradd --no-create-home appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/livez || exit 1
CMD ["uv", "run", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--workers", "4"]
```

**Key rules:**
- `USER appuser` in production is **mandatory** — automatic fail in any security review.
- Copy `pyproject.toml` + `uv.lock` **before** `COPY . .` to preserve Docker layer cache.
- Do **not** use `latest` for the base image — pin to a version digest for supply-chain integrity.

### 3. `docker-compose.yml`

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    env_file:
      - .env.development
    depends_on:
      - db

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- Remove `db` / `redis` sidecars if the app doesn't use them.
- `env_file: .env.development` — **never** `env_file: .env`.

### 4. Health endpoint in app code

Add to FastAPI / Flask app. Two distinct endpoints:

```python
from fastapi import FastAPI, Response, status

app = FastAPI()

@app.get("/livez", status_code=200)
def livez() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    checks = {"db": await db.ping(), "cache": await cache.ping()}
    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
```

`livez` must NOT touch external deps. `readyz` checks deps.

### 5. Build and run

```bash
docker compose up --build app
curl -f http://localhost:8000/livez
curl -f http://localhost:8000/readyz
```

Both must return 200 (or 503 for readyz if deps are down, which is correct behaviour).

### 6. Commit

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "build: add multi-stage Dockerfile, compose, and healthchecks"
```

## Pitfalls to avoid

- **`USER root` in production** — automatic fail in any security review.
- **`COPY . .` before deps** — breaks Docker layer cache, every code change reinstalls deps.
- **No `.dockerignore`** — `.venv/` and `.git/` end up in the image (huge + leaks).
- **`latest` tag for base image** — non-reproducible builds.
- **No `HEALTHCHECK`** — orchestrator can't tell live from dead.

## Hand-off

Recommend `scaffold-observability` next.
