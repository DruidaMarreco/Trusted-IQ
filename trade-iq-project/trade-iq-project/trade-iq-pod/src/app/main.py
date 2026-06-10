"""FastAPI application factory.

All dependency wiring lives here — LLMs built once at startup,
injected into agents, agents injected into routes.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.agents.orchestrator import OrchestratorAgent
from app.agents.subagent_a import SubagentA
from app.agents.subagent_b import SubagentB
from app.api.routes import router, set_orchestrator
from app.config import settings
from app.llm_factory import build_llm
from app.logging import bind_request_id, configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        debug=settings.debug,
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request,
        call_next: "Callable[[Request], Awaitable[Response]]",
    ) -> Response:
        """Attach X-Request-ID to every request and response."""
        import structlog.contextvars

        structlog.contextvars.clear_contextvars()
        rid = bind_request_id(request.headers.get("X-Request-ID"))
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.get("/livez", tags=["health"], summary="Liveness probe")
    async def livez() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"], summary="Readiness probe")
    async def readyz() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    # Build LLMs — each agent can use a different model/provider
    orchestrator_llm = build_llm(model=settings.orchestrator_model or None)
    subagent_a_llm = build_llm(model=settings.subagent_a_model or None)
    subagent_b_llm = build_llm(model=settings.subagent_b_model or None)

    # Wire agents
    orchestrator = OrchestratorAgent(
        llm=orchestrator_llm,
        subagent_a=SubagentA(subagent_a_llm),
        subagent_b=SubagentB(subagent_b_llm),
    )
    set_orchestrator(orchestrator)

    app.include_router(router)
    logger.info("app_started", env=settings.env, version=settings.app_version)
    return app


app = create_app()
