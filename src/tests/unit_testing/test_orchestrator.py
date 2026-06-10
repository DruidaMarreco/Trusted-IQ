"""Unit tests for the agent orchestrator (classify -> route -> grounded response)."""

import json
from collections.abc import Callable

import pytest
from langchain_core.language_models import BaseChatModel

from app.agents.orchestrator import OrchestratorAgent

_LLM = Callable[..., BaseChatModel]

INTENT_DATA = json.dumps({"intent": "DATA_QUERY", "confidence": 0.95, "extracted_params": {"account": "Tesco"}})
INTENT_OPT = json.dumps({"intent": "OPTIMIZER_RUN", "confidence": 0.9, "extracted_params": {"budget_remaining": 80000}})
INTENT_CLARIFY = json.dumps({"intent": "CLARIFICATION", "confidence": 0.4, "clarifying_question": "Which account?"})
INTENT_OOS = json.dumps({"intent": "OUT_OF_SCOPE", "confidence": 0.99, "extracted_params": {}})


@pytest.mark.asyncio
async def test_data_query_routes_to_texttosql_and_grounds(make_llm: _LLM) -> None:
    llm = make_llm(INTENT_DATA, "The Easter display delivered **142% ROI**.")
    result = await OrchestratorAgent(llm).run("Why did you recommend the Easter display for Tesco?")
    assert result.intent == "DATA_QUERY"
    assert result.tool == "text_to_sql_lookup"
    assert "142%" in result.answer
    assert result.tool_output["row_count"] >= 1


@pytest.mark.asyncio
async def test_optimizer_run_routes_to_optimizer(make_llm: _LLM) -> None:
    llm = make_llm(INTENT_OPT, "Here are the best options within budget.")
    result = await OrchestratorAgent(llm).run("Best promo options for my remaining £80k?")
    assert result.intent == "OPTIMIZER_RUN"
    assert result.tool == "optimizer_run"
    assert result.tool_output["budget"] == 80000


@pytest.mark.asyncio
async def test_clarification_returns_question_and_no_tool(make_llm: _LLM) -> None:
    result = await OrchestratorAgent(make_llm(INTENT_CLARIFY)).run("show me options")
    assert result.intent == "CLARIFICATION"
    assert result.tool is None
    assert "account" in result.answer.lower()


@pytest.mark.asyncio
async def test_out_of_scope_declines_and_no_tool(make_llm: _LLM) -> None:
    result = await OrchestratorAgent(make_llm(INTENT_OOS)).run("what's the weather?")
    assert result.intent == "OUT_OF_SCOPE"
    assert result.tool is None
