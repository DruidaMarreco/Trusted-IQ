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


def example_agent_invoke() -> None:
    """POST /agent/invoke — runs the orchestrator (calls the configured LLM)."""
    print("\n# POST /agent/invoke")
    payload = {
        "query": "Why did you recommend the Easter display for Tesco?",
        "session_id": "demo-session-1",
    }
    print("request:", payload)
    try:
        r = client.post("/agent/invoke", json=payload)
        print("status:", r.status_code)
        print("response:", r.json())
    except Exception as exc:  # a working LLM backend / auth is required here
        print("agent call failed (needs a working LLM backend / auth):", exc)


def main() -> None:
    print("TradeIQ assistant — endpoint integration examples")
    example_health()
    example_agent_invoke()


if __name__ == "__main__":
    main()
