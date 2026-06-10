"""Unit tests for call-cost estimation and turn-metric aggregation."""

from app.metrics import CallMetrics, TurnMetrics, estimate_cost


def test_estimate_cost_known_model() -> None:
    # gpt-4o: 0.0025 in / 0.010 out per 1k tokens
    assert estimate_cost("gpt-4o", 1000, 1000) == 0.0125
    assert estimate_cost("gpt-4o", 0, 0) == 0.0


def test_estimate_cost_unknown_model_is_zero() -> None:
    assert estimate_cost("mystery-model", 1000, 1000) == 0.0


def test_turn_metrics_aggregate() -> None:
    turn = TurnMetrics()
    turn.add(CallMetrics(model="opus", latency_ms=120.0, input_tokens=100, output_tokens=50, cost_usd=0.001))
    turn.add(CallMetrics(model="opus", latency_ms=80.0, input_tokens=40, output_tokens=20, cost_usd=0.0005))
    assert turn.calls == 2
    assert turn.input_tokens == 140
    assert turn.output_tokens == 70
    assert turn.latency_ms == 200.0
    assert turn.cost_usd == 0.0015
    assert turn.as_dict()["calls"] == 2
