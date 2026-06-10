"""Unit tests for the /agent/invoke route — orchestrator wiring, response shape,
and context (account_scope / planning_period / history) pass-through. No LLM."""

import json
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient as _TestClient

import app.api.routes as routes_module
from app.agents.orchestrator import OrchestratorAgent, OrchestratorResult
from app.api.routes import router, set_orchestrator
from app.metrics import CallMetrics, TurnMetrics


class _FakeOrchestrator:
    """Records the call and returns a canned result — stands in for the real agent."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run(
        self,
        query: str,
        *,
        history: str = "[]",
        account_scope: str = "",
        planning_period: str = "",
    ) -> OrchestratorResult:
        self.calls.append(
            {"query": query, "history": history, "account_scope": account_scope, "planning_period": planning_period}
        )
        metrics = TurnMetrics()
        metrics.add(CallMetrics(model="haiku", latency_ms=12.0, input_tokens=100, output_tokens=50, cost_usd=0.001))
        return OrchestratorResult(
            answer="The Easter display delivered **142% ROI**.",
            intent="DATA_QUERY",
            confidence=0.95,
            tool="text_to_sql_lookup",
            params={"account": "Tesco"},
            tool_output={"row_count": 1},
            metrics=metrics,
        )


def _client(orchestrator: object) -> _TestClient:
    set_orchestrator(cast(OrchestratorAgent, orchestrator))
    app = FastAPI()
    app.include_router(router)
    return _TestClient(app)


def test_invoke_returns_answer_intent_tool_and_metrics() -> None:
    orchestrator = _FakeOrchestrator()
    client = _client(orchestrator)

    resp = client.post(
        "/agent/invoke",
        json={
            "query": "Why did you recommend the Easter display for Tesco?",
            "session_id": "demo-1",
            "account_scope": "Tesco UK",
            "planning_period": "FY2025",
            "history": [{"role": "user", "content": "hi"}],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "142%" in body["result"]
    assert body["intent"] == "DATA_QUERY"
    assert body["tool"] == "text_to_sql_lookup"
    assert body["session_id"] == "demo-1"
    assert body["metadata"]["confidence"] == 0.95
    assert body["metadata"]["metrics"]["calls"] == 1

    # Context is forwarded to the orchestrator.
    call = orchestrator.calls[0]
    assert call["account_scope"] == "Tesco UK"
    assert call["planning_period"] == "FY2025"
    assert json.loads(call["history"]) == [{"role": "user", "content": "hi"}]


def test_invoke_returns_503_when_orchestrator_not_wired() -> None:
    app = FastAPI()
    app.include_router(router)
    routes_module._orchestrator = None  # simulate startup not having wired it
    resp = _TestClient(app).post("/agent/invoke", json={"query": "hi"})
    assert resp.status_code == 503
