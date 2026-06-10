"""Integration examples — exercise the TradeIQ assistant API endpoints.

Run:  make integration   (or)   uv run python src/integration_testing/test.py

This is the "singular tests" tier: a hands-on walkthrough of every HTTP
endpoint using FastAPI's TestClient, with example requests and responses.
It complements the other tiers:
  - src/tests/unit_testing   — fast, mocked unit tests (no network)
  - src/integration_testing  — THIS: real endpoint calls, example payloads
  - src/metrics_testing      — mass model evaluation with an HTML report

The /agent/invoke example uses whatever LLM backend is configured; by default
it points at Claude Code (subscription quota). Override via env vars.

Tool backends: by default the orchestrator uses the deterministic MOCK tools
(no CDT_BASE_URL / ERDC_BASE_URL set), so this runs end-to-end with no external
services. To exercise the LIVE CDT TextToSQL / ERDC Optimizer services, set their
endpoints before running, e.g.:

    CDT_BASE_URL=https://cdt.internal/api  CDT_API_KEY=...  \
    ERDC_BASE_URL=https://erdc.internal/api  ERDC_API_KEY=... \
        uv run python src/integration_testing/test.py
"""

from __future__ import annotations

import os

# Configure a no-key backend BEFORE importing the app — create_app() builds the
# LLMs at import time. Claude Code draws on the subscription quota.
os.environ.setdefault("LLM_PROVIDER", "claude_code")
os.environ.setdefault("LLM_MODEL", "haiku")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def example_health() -> None:
    """Liveness/readiness probes — no LLM needed."""
    print("\n# GET /livez")
    r = client.get("/livez")
    print(r.status_code, r.json())

    print("\n# GET /readyz")
    r = client.get("/readyz")
    print(r.status_code, r.json())


# One example per intent — DATA_QUERY + OPTIMIZER_RUN route to a tool;
# CLARIFICATION + OUT_OF_SCOPE resolve without one.
_EXAMPLES = [
    {
        "label": "DATA_QUERY -> CDT TextToSQL",
        "query": "Why did you recommend the Easter display for Tesco?",
        "session_id": "demo-data-query",
        "account_scope": "Tesco, Sainsbury's UK",
        "planning_period": "FY2025",
    },
    {
        "label": "OPTIMIZER_RUN -> ERDC Optimizer",
        "query": "What are the best promo options for my remaining £80k budget?",
        "session_id": "demo-optimizer",
    },
    {
        "label": "CLARIFICATION (no tool)",
        "query": "show me the options",
        "session_id": "demo-clarify",
    },
    {
        "label": "OUT_OF_SCOPE (no tool)",
        "query": "What's the weather in London today?",
        "session_id": "demo-oos",
    },
]


def example_agent_invoke() -> None:
    """POST /agent/invoke for each intent — runs the orchestrator end-to-end."""
    for example in _EXAMPLES:
        label = example.pop("label")
        print(f"\n# POST /agent/invoke — {label}")
        print("request:", example)
        try:
            r = client.post("/agent/invoke", json=example)
            print("status:", r.status_code)
            if r.status_code == 200:
                body = r.json()
                print("intent:", body["intent"], "| tool:", body["tool"])
                print("metrics:", body["metadata"].get("metrics"))
                print("answer:", body["result"])
            else:
                print("response:", r.json())
        except Exception as exc:  # a working LLM backend / auth is required here
            print("agent call failed (needs a working LLM backend / auth):", exc)


def main() -> None:
    print("TradeIQ assistant — endpoint integration examples")
    example_health()
    example_agent_invoke()


if __name__ == "__main__":
    main()
