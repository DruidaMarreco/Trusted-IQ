"""Unit tests for the orchestrator agent."""

import pytest

from app.agents.orchestrator import OrchestratorAgent


@pytest.mark.asyncio
async def test_orchestrator_returns_string(mock_orchestrator: OrchestratorAgent) -> None:
    result = await mock_orchestrator.run("test query")
    assert isinstance(result, str)
    assert result == "final_answer"
