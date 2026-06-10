"""Shared pytest fixtures."""

from unittest.mock import AsyncMock

import pytest

from app.agents.orchestrator import OrchestratorAgent


@pytest.fixture
def mock_orchestrator(monkeypatch: pytest.MonkeyPatch) -> OrchestratorAgent:
    """OrchestratorAgent with LLM calls mocked out."""
    agent = OrchestratorAgent.__new__(OrchestratorAgent)
    agent._subagent_a = AsyncMock()  # type: ignore[attr-defined]
    agent._subagent_a.run = AsyncMock(return_value="subagent_a_result")
    agent._subagent_b = AsyncMock()  # type: ignore[attr-defined]
    agent._subagent_b.run = AsyncMock(return_value="subagent_b_result")
    # Mock new langchain 0.3+ agent (CompiledStateGraph)
    agent._agent = AsyncMock()  # type: ignore[attr-defined]
    agent._agent.ainvoke = AsyncMock(return_value={"messages": [AsyncMock(content="final_answer")]})
    return agent
