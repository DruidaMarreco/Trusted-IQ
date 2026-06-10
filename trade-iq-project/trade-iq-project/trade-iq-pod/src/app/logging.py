"""Structured logging configuration with correlation IDs."""
import logging
import uuid
from contextvars import ContextVar

import structlog

from app.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def bind_request_id(request_id: str | None = None) -> str:
    """Bind a request ID to the current context; generate one if not provided."""
    rid = request_id or str(uuid.uuid4())
    request_id_var.set(rid)
    structlog.contextvars.bind_contextvars(request_id=rid)
    return rid


def configure_logging() -> None:
    """Configure structlog — pretty console in dev, JSON in staging/prod."""
    renderer: structlog.types.Processor = (
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
        cache_logger_on_first_use=True,
    )
