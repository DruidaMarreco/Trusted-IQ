"""Unit tests for the TPO tool integrations: mock behaviour, intent routing,
the live HTTP path, mock fallback, and HTTP error handling."""

from typing import Any

import httpx
import pytest

from app.config import Settings
from app.tools import ToolError, http, mock, route_to_tool

_MOCK_CFG = Settings(cdt_base_url="", erdc_base_url="")
_LIVE_CFG = Settings(cdt_base_url="https://cdt.example/api", erdc_base_url="https://erdc.example/api")


# --- deterministic mock implementations ---
def test_mock_text_to_sql_returns_account_rows() -> None:
    out = mock.text_to_sql_lookup({"account": "Tesco"})
    assert out["row_count"] >= 1
    assert all(r["account"] == "Tesco" for r in out["rows"])


def test_mock_text_to_sql_unknown_account_is_empty() -> None:
    out = mock.text_to_sql_lookup({"account": "Nonexistent Retailer"})
    assert out["row_count"] == 0
    assert out["rows"] == []


def test_mock_optimizer_respects_budget() -> None:
    out = mock.optimizer_run({"budget_remaining": 40000})
    assert out["budget_used"] <= 40000
    assert out["selected_count"] >= 1
    assert 0 <= out["budget_utilisation_pct"] <= 100


# --- routing + mock fallback (no base URL configured) ---
@pytest.mark.asyncio
async def test_route_data_query_falls_back_to_mock() -> None:
    name, desc, out = await route_to_tool("DATA_QUERY", {"account": "Tesco"}, _MOCK_CFG, query="why Tesco?")
    assert name == "text_to_sql_lookup"
    assert "CDT" in desc
    assert out["row_count"] >= 1


@pytest.mark.asyncio
async def test_route_optimizer_falls_back_to_mock() -> None:
    name, _desc, out = await route_to_tool("OPTIMIZER_RUN", {"budget_remaining": 50000}, _MOCK_CFG)
    assert name == "optimizer_run"
    assert out["budget_used"] <= 50000


@pytest.mark.asyncio
async def test_route_other_intents_invoke_no_tool() -> None:
    assert (await route_to_tool("OUT_OF_SCOPE", {}, _MOCK_CFG))[0] == "none"
    assert (await route_to_tool("CLARIFICATION", {}, _MOCK_CFG))[0] == "none"


# --- live HTTP path (call_json patched, no network) ---
@pytest.mark.asyncio
async def test_cdt_live_path_builds_request_and_normalises(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_call_json(base_url: str, path: str, payload: dict[str, Any], **_: Any) -> dict[str, Any]:
        captured.update(base_url=base_url, path=path, payload=payload)
        return {"rows": [{"account": "Tesco", "roi_predicted_pct": 142}], "row_count": 1, "sql": "SELECT 1"}

    monkeypatch.setattr(http, "call_json", fake_call_json)
    name, _desc, out = await route_to_tool("DATA_QUERY", {"account": "Tesco"}, _LIVE_CFG, query="why Tesco?")

    assert name == "text_to_sql_lookup"
    assert out["row_count"] == 1 and out["sql"] == "SELECT 1"
    assert captured["base_url"] == "https://cdt.example/api"
    assert captured["path"] == "/query"
    assert captured["payload"] == {"question": "why Tesco?", "account": "Tesco"}


@pytest.mark.asyncio
async def test_erdc_live_path_builds_request(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call_json(base_url: str, path: str, payload: dict[str, Any], **_: Any) -> dict[str, Any]:
        return {"currency": "GBP", "budget": payload["budget_remaining"], "options": [], "selected_count": 0}

    monkeypatch.setattr(http, "call_json", fake_call_json)
    name, _desc, out = await route_to_tool("OPTIMIZER_RUN", {"budget_remaining": 80000}, _LIVE_CFG)

    assert name == "optimizer_run"
    assert out["budget"] == 80000


# --- HTTP helper error handling ---
class _FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("POST", "https://x.example/q")

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=httpx.Response(self.status_code))


def _client_returning(resp: _FakeResponse) -> type:
    class _Client:
        def __init__(self, *_: Any, **__: Any) -> None: ...
        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def post(self, *_: Any, **__: Any) -> _FakeResponse:
            return resp

    return _Client


@pytest.mark.asyncio
async def test_call_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", _client_returning(_FakeResponse(200, {"ok": True})))
    out = await http.call_json("https://x.example", "/q", {}, retries=0)
    assert out == {"ok": True}


@pytest.mark.asyncio
async def test_call_json_client_error_raises_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", _client_returning(_FakeResponse(404, {})))
    with pytest.raises(ToolError):
        await http.call_json("https://x.example", "/q", {}, retries=2)


@pytest.mark.asyncio
async def test_call_json_transport_error_raises_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailClient:
        def __init__(self, *_: Any, **__: Any) -> None: ...
        async def __aenter__(self) -> "_FailClient":
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def post(self, *_: Any, **__: Any) -> Any:
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", _FailClient)
    with pytest.raises(ToolError):
        await http.call_json("https://x.example", "/q", {}, retries=0)
