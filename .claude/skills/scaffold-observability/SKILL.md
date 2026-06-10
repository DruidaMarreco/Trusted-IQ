---
name: scaffold-observability
description: Use this skill when the user asks to set up structured logging, pydantic-settings, Sentry error tracking, OpenTelemetry tracing, or correlation IDs for a Python application. Covers Phase 6 of the engineering Quickstart.
---

# Scaffold Observability (Fase 6)

Wires `pydantic-settings` (config validation at boot), `structlog` (JSON logs + correlation IDs), Sentry (error tracking), and OpenTelemetry (distributed tracing).

## When to use

- "Configurar logging"
- "Settings com pydantic"
- "Integrar Sentry"
- "OpenTelemetry"
- "Correlation IDs"

## Decisions to confirm with the user

1. **Sentry / GlitchTip?** (default Sentry SaaS; GlitchTip if data residency matters).
2. **OpenTelemetry exporter?** (Jaeger, Tempo, Datadog, none-for-now).
3. **Is this a microservice?** (if yes → OTel is mandatory).

## Steps

### 1. Add dependencies

```bash
uv add pydantic-settings structlog
uv add sentry-sdk[fastapi]                     # if Sentry
uv add opentelemetry-distro opentelemetry-instrumentation-fastapi \
       opentelemetry-instrumentation-httpx \
       opentelemetry-instrumentation-sqlalchemy   # if OTel
```

### 2. `src/<pkg>/settings.py`

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",           # fails on undeclared env vars
    )

    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    api_key: SecretStr              # required, no default
    database_url: str
    llm_model: str = Field(default="gemini-2.0-flash")
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)
    sentry_dsn: SecretStr | None = None
    app_version: str = Field(default="dev")

settings = Settings()   # app fails at boot if env invalid
```

**Rules:**
- `SecretStr` for secrets — won't appear in logs or `repr()`.
- `extra="forbid"` — typos in `.env` are caught immediately.
- Module-level `Settings()` — fail early at boot, not 3 h later with `NoneType` errors.

### 3. `src/<pkg>/logging.py`

```python
import logging
import uuid
from contextvars import ContextVar

import structlog

from .settings import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def bind_request_id(request_id: str | None = None) -> str:
    rid = request_id or str(uuid.uuid4())
    request_id_var.set(rid)
    structlog.contextvars.bind_contextvars(request_id=rid)
    return rid


def configure_logging() -> None:
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.env == "dev"
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
    )
```

### 4. FastAPI middleware for correlation IDs

```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or bind_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response
```

### 5. Sentry init (in `main.py` or app factory)

```python
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.env,
        release=settings.app_version,
        traces_sample_rate=0.1,
        send_default_pii=False,
        integrations=[FastApiIntegration()],
    )
```

**Never** initialise Sentry with `send_default_pii=True` without explicit user consent + privacy review.

### 6. OpenTelemetry (if applicable)

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
```

Plus exporter config via env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`).

### 7. Update `.env.example`

Add all new env vars with example values (no secrets):

```bash
ENV=dev
LOG_LEVEL=INFO
API_KEY=changeme
DATABASE_URL=postgresql://localhost/myapp
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=my-service
```

### 8. Forbidden patterns — search and remove

Before committing, grep for:
- `print(` in `src/` — replace with `logger.info(...)`.
- `os.getenv(` in `src/` — replace with `settings.<field>`.
- `except Exception: pass` — replace with specific catch + log + re-raise.

### 9. Commit

```bash
git add src/ .env.example pyproject.toml uv.lock
git commit -m "feat(observability): add pydantic-settings, structlog, Sentry, OTel"
```

## Hand-off

Recommend `scaffold-docs-governance` next.
