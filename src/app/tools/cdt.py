"""CDT TextToSQL agent integration — the DATA_QUERY tool.

Calls the external CDT service (which owns NL->SQL generation and SQL MI access)
when ``cfg.cdt_base_url`` is set; otherwise returns deterministic mock rows.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.tools import http, mock


class CDTQueryRequest(BaseModel):
    """Request payload for the CDT TextToSQL service."""

    question: str = ""
    account: str | None = None
    time_period: str | None = None
    sku: str | None = None


async def text_to_sql_lookup(params: dict[str, Any], cfg: Settings, *, question: str = "") -> dict[str, Any]:
    """Return recommendation rows for the user's query.

    Live CDT service when configured, deterministic mock otherwise. The result
    is normalised to ``{"rows": [...], "row_count": int, "sql"?: str}`` — the
    shape the Response Generator and groundedness check expect.
    """
    if not cfg.cdt_base_url:
        return mock.text_to_sql_lookup(params)

    request = CDTQueryRequest(
        question=question,
        account=params.get("account"),
        time_period=params.get("time_period"),
        sku=params.get("sku"),
    )
    raw = await http.call_json(
        cfg.cdt_base_url,
        "/query",
        request.model_dump(exclude_none=True),
        api_key=cfg.cdt_api_key.get_secret_value(),
        timeout=cfg.cdt_timeout_s,
        retries=cfg.tool_max_retries,
    )
    rows = raw.get("rows", [])
    result: dict[str, Any] = {"rows": rows, "row_count": int(raw.get("row_count", len(rows)))}
    if "sql" in raw:
        result["sql"] = raw["sql"]
    return result
