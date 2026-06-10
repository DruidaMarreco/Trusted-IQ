"""TPO tool integrations for the thin orchestrator.

Two external systems back the two tool-using intents:

    DATA_QUERY    -> CDT TextToSQL agent over SQL MI   (app.tools.cdt)
    OPTIMIZER_RUN -> ERDC Optimizer API                (app.tools.erdc)

Each tool calls its **live** service over HTTP when a base URL is configured
(``CDT_BASE_URL`` / ``ERDC_BASE_URL``), and otherwise falls back to
deterministic **mock** output (``app.tools.mock``) so local dev, unit tests and
the model evaluation run without the live systems. The orchestrator stays thin:
it never owns SQL generation or database credentials — CDT does.
"""

from app.tools.http import ToolError
from app.tools.registry import route_to_tool

__all__ = ["ToolError", "route_to_tool"]
