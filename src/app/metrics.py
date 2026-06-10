"""Per-call LLM metrics: latency, token usage and estimated cost.

Captured for every model call in the orchestrator, attached to the response
metadata, and emitted via structlog (App Insights / Azure Monitor friendly).
"""

from __future__ import annotations

from dataclasses import dataclass

# Published USD price per 1k tokens: (input, output). Claude Code aliases map to
# their family's API price (informative; subscription usage is quota-billed).
_PRICES: dict[str, tuple[float, float]] = {
    "gpt-5": (0.015, 0.060),
    "gpt-4o": (0.0025, 0.010),
    "gpt-4o-mini": (0.00015, 0.0006),
    "opus": (0.005, 0.025),
    "claude-opus-4-8": (0.005, 0.025),
    "sonnet": (0.003, 0.015),
    "claude-sonnet-4-6": (0.003, 0.015),
    "haiku": (0.001, 0.005),
    "claude-haiku-4-5": (0.001, 0.005),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a call from the model's published token prices."""
    input_price, output_price = _PRICES.get(model, (0.0, 0.0))
    return input_tokens / 1000 * input_price + output_tokens / 1000 * output_price


@dataclass
class CallMetrics:
    """Metrics for a single LLM call."""

    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class TurnMetrics:
    """Aggregated metrics for one orchestration turn (one or more calls)."""

    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0

    def add(self, call: CallMetrics) -> None:
        self.latency_ms = round(self.latency_ms + call.latency_ms, 1)
        self.input_tokens += call.input_tokens
        self.output_tokens += call.output_tokens
        self.cost_usd = round(self.cost_usd + call.cost_usd, 6)
        self.calls += 1

    def as_dict(self) -> dict[str, float | int]:
        return {
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "calls": self.calls,
        }
