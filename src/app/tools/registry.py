"""Intent -> tool routing for the thin orchestrator.

The single place intents are mapped to tools. Adding a new tool-using intent
means adding one branch here; the orchestrator control flow stays unchanged.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.tools import cdt, erdc


async def route_to_tool(
    intent: str,
    params: dict[str, Any],
    cfg: Settings,
    *,
    query: str = "",
) -> tuple[str, str, dict[str, Any]]:
    """Route a classified intent to its tool.

    Returns ``(tool_name, description, tool_output)``. Raises
    :class:`app.tools.ToolError` if a configured live service call fails.
    """
    if intent == "DATA_QUERY":
        output = await cdt.text_to_sql_lookup(params, cfg, question=query)
        return ("text_to_sql_lookup", "CDT TextToSQL agent over SQL MI", output)
    if intent == "OPTIMIZER_RUN":
        output = await erdc.optimizer_run(params, cfg)
        return ("optimizer_run", "ERDC Optimizer API", output)
    return ("none", "no tool invoked", {})
