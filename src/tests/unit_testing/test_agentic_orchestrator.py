"""Unit tests for the agentic orchestrator's pure helpers (no SDK / no network).

The live agentic tool-use path is exercised by
``src/integration_testing/agentic_tool_test.py``, which needs the Claude Agent
SDK and the subscription quota; here we only cover the deterministic bits.
"""

from app.agents.agentic_orchestrator import AgenticResult, _coerce_model
from app.metrics import TurnMetrics


def test_coerce_model_maps_full_ids_and_aliases() -> None:
    assert _coerce_model("opus") == "opus"
    assert _coerce_model("haiku") == "haiku"
    assert _coerce_model("claude-opus-4-8") == "opus"
    assert _coerce_model("claude-sonnet-4-6") == "sonnet"
    assert _coerce_model("claude-haiku-4-5") == "haiku"
    assert _coerce_model("gpt-4o") == "sonnet"  # unknown -> safe default


def test_tool_names_strips_namespace_and_filters_toolsearch() -> None:
    result = AgenticResult(
        answer="ok",
        tools_used=[
            {"name": "ToolSearch", "input": {}},  # SDK discovery step — must be filtered out
            {"name": "mcp__tpo__optimizer_run", "input": {}},
            {"name": "mcp__tpo__text_to_sql_lookup", "input": {}},
        ],
        metrics=TurnMetrics(),
    )
    assert result.tool_names == ["optimizer_run", "text_to_sql_lookup"]


def test_tool_names_empty_when_no_tool_used() -> None:
    assert AgenticResult(answer="clarify please").tool_names == []
