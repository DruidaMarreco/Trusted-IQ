"""ERDC Optimizer API integration — the OPTIMIZER_RUN tool.

Calls the external ERDC Optimizer REST API when ``cfg.erdc_base_url`` is set;
otherwise returns deterministic mock options within the budget.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings
from app.tools import http, mock


class OptimiseRequest(BaseModel):
    """Request payload for the ERDC Optimizer API."""

    budget_remaining: int = Field(default=100_000, ge=0)
    objective: str = "maximise ROI"
    account: str | None = None


async def optimizer_run(params: dict[str, Any], cfg: Settings) -> dict[str, Any]:
    """Return ranked promotion options within the budget.

    Live ERDC API when configured, deterministic mock otherwise.
    """
    if not cfg.erdc_base_url:
        return mock.optimizer_run(params)

    request = OptimiseRequest(
        budget_remaining=int(params.get("budget_remaining") or 100_000),
        objective=str(params.get("objective") or "maximise ROI"),
        account=params.get("account"),
    )
    return await http.call_json(
        cfg.erdc_base_url,
        "/optimise",
        request.model_dump(exclude_none=True),
        api_key=cfg.erdc_api_key.get_secret_value(),
        timeout=cfg.erdc_timeout_s,
        retries=cfg.tool_max_retries,
    )
