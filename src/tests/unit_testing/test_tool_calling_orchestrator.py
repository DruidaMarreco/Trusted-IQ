"""Unit tests for the native tool-calling orchestrator — the bind_tools loop,
with a scripted fake LLM (no network). The live path is covered by
src/integration_testing (Azure gpt-4o)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.tool_calling_orchestrator import ToolCallingOrchestrator
from app.config import Settings

_MOCK_CFG = Settings(cdt_base_url="", erdc_base_url="")


def _fake_llm(*responses: AIMessage) -> MagicMock:
    """A chat model whose bound form returns the scripted messages in order."""
    llm = MagicMock()
    llm.model_name = "gpt-4o"
    bound = MagicMock()
    bound.ainvoke = AsyncMock(side_effect=list(responses))
    llm.bind_tools.return_value = bound
    return llm


@pytest.mark.asyncio
async def test_model_calls_optimizer_then_answers() -> None:
    tool_call = AIMessage(
        content="",
        tool_calls=[{"name": "optimizer_run", "args": {"budget_remaining": 80000}, "id": "c1", "type": "tool_call"}],
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    final = AIMessage(
        content="Here are your options.", usage_metadata={"input_tokens": 200, "output_tokens": 40, "total_tokens": 240}
    )
    agent = ToolCallingOrchestrator(llm=_fake_llm(tool_call, final), cfg=_MOCK_CFG)

    result = await agent.run("Best options for my £80k budget at Tesco?")
    assert result.tool_names == ["optimizer_run"]
    assert result.answer == "Here are your options."
    assert result.num_turns == 2
    assert result.metrics.calls == 2
    assert result.metrics.input_tokens == 300


@pytest.mark.asyncio
async def test_no_tool_when_model_answers_directly() -> None:
    final = AIMessage(
        content="Could you tell me which account?",
        usage_metadata={"input_tokens": 50, "output_tokens": 10, "total_tokens": 60},
    )
    agent = ToolCallingOrchestrator(llm=_fake_llm(final), cfg=_MOCK_CFG)

    result = await agent.run("show me the options")
    assert result.tool_names == []
    assert result.num_turns == 1
    assert "account" in result.answer.lower()


@pytest.mark.asyncio
async def test_tool_output_is_grounded_in_mock() -> None:
    """The executed tool returns real mock data (no network), fed back to the model."""
    tool_call = AIMessage(
        content="",
        tool_calls=[{"name": "text_to_sql_lookup", "args": {"account": "Tesco"}, "id": "c1", "type": "tool_call"}],
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    final = AIMessage(
        content="142% ROI.", usage_metadata={"input_tokens": 200, "output_tokens": 30, "total_tokens": 230}
    )
    agent = ToolCallingOrchestrator(llm=_fake_llm(tool_call, final), cfg=_MOCK_CFG)
    result = await agent.run("Why Tesco?")
    assert result.tool_names == ["text_to_sql_lookup"]
    assert result.answer == "142% ROI."
