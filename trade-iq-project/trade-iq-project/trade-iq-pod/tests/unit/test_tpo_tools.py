"""Unit tests for the mock TPO tools."""

from app.tpo_tools import optimizer_run, route_to_tool, text_to_sql_lookup


def test_text_to_sql_returns_account_rows() -> None:
    out = text_to_sql_lookup({"account": "Tesco"})
    assert out["row_count"] >= 1
    assert all(r["account"] == "Tesco" for r in out["rows"])


def test_text_to_sql_unknown_account_is_empty() -> None:
    out = text_to_sql_lookup({"account": "Nonexistent Retailer"})
    assert out["row_count"] == 0
    assert out["rows"] == []


def test_optimizer_respects_budget() -> None:
    out = optimizer_run({"budget_remaining": 40000})
    assert out["budget_used"] <= 40000
    assert out["selected_count"] >= 1
    assert 0 <= out["budget_utilisation_pct"] <= 100


def test_route_to_tool_maps_intents() -> None:
    assert route_to_tool("DATA_QUERY", {"account": "Tesco"})[0] == "text_to_sql_lookup"
    assert route_to_tool("OPTIMIZER_RUN", {"budget_remaining": 50000})[0] == "optimizer_run"
    assert route_to_tool("OUT_OF_SCOPE", {})[0] == "none"
