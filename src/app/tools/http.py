"""Shared async HTTP helper for TPO tool integrations (CDT, ERDC).

A small, dependency-light client around ``httpx`` with retries on transient
failures, structured logging and a single ``ToolError`` for callers to catch.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class ToolError(RuntimeError):
    """A TPO tool (CDT / ERDC) call failed after exhausting retries."""


async def call_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    api_key: str = "",
    timeout: float = 30.0,
    retries: int = 2,
) -> dict[str, Any]:
    """POST ``payload`` as JSON to ``base_url + path`` and return the JSON body.

    Retries transient failures (network errors and 5xx responses) with linear
    backoff. Raises :class:`ToolError` on client errors (4xx, not retried) or
    once retries are exhausted.
    """
    url = base_url.rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ToolError(f"expected a JSON object from {url}, got {type(data).__name__}")
            return data
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code < 500:
                logger.error("tool_http_client_error", url=url, status=exc.response.status_code)
                break  # client error — retrying won't help
            logger.warning("tool_http_server_error", url=url, status=exc.response.status_code, attempt=attempt)
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("tool_http_transport_error", url=url, attempt=attempt, error=str(exc))
        if attempt < retries:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise ToolError(f"tool call failed: {url}: {last_error}") from last_error
