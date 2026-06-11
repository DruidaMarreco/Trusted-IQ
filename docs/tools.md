# Tool integrations — CDT TextToSQL & ERDC Optimizer

The two tool-using intents are backed by two external systems. This document
describes the integration layer in [`src/app/tools/`](../src/app/tools/): its
design, the request/response contracts, configuration, error handling, and how
to test the live path before the real services exist.

| Intent | Tool | Backing system | Module |
|---|---|---|---|
| `DATA_QUERY` | `text_to_sql_lookup` | **CDT TextToSQL agent** over SQL MI | [`tools/cdt.py`](../src/app/tools/cdt.py) |
| `OPTIMIZER_RUN` | `optimizer_run` | **ERDC Optimizer API** | [`tools/erdc.py`](../src/app/tools/erdc.py) |

## Design: live-or-mock per tool

Each tool calls its **live** service over HTTP when a base URL is configured,
and otherwise returns **deterministic mock** output. This single switch is the
core of the design:

```
cdt.text_to_sql_lookup(params, cfg, question)
    if cfg.cdt_base_url:  → POST {cfg.cdt_base_url}/query   (live)
    else:                 → mock.text_to_sql_lookup(params) (deterministic)
```

Why it matters:

- **Local dev, unit tests and the model evaluation run with zero external
  dependencies** — the mock returns the same JSON shape the live service would.
- **Going live is a configuration change, not a code change** — set the base URL
  and key in `.env`.
- **Reproducible evaluation** — the eval forces empty tool URLs, so groundedness
  scores never depend on a live service.

### Package layout

| Module | Responsibility |
|---|---|
| `registry.py` | `route_to_tool(intent, params, cfg, *, query)` — the single intent→tool map |
| `cdt.py` | CDT TextToSQL: `CDTQueryRequest` schema + live-or-mock dispatch |
| `erdc.py` | ERDC Optimizer: `OptimiseRequest` schema + live-or-mock dispatch |
| `http.py` | Shared async `httpx` client: retries, `Bearer` auth, `ToolError` |
| `mock.py` | Synthetic, deterministic data (Tesco/Carrefour recs, optimizer candidates) |
| `__init__.py` | Public surface: `route_to_tool`, `ToolError` |

## Contracts

The orchestrator builds a typed request from the classified params and the
user's natural-language question, POSTs it, and normalises the response.

### CDT TextToSQL — `POST {CDT_BASE_URL}/query`

Request (`CDTQueryRequest`, `None` fields omitted):

```json
{ "question": "Why did you recommend the Easter display for Tesco?",
  "account": "Tesco", "time_period": "April 2025", "sku": "KitKat 4-pack" }
```

Expected response (extra fields ignored; normalised to):

```json
{ "rows": [ { "account": "Tesco", "sku": "KitKat 4-pack", "roi_predicted_pct": 142, ... } ],
  "row_count": 1, "sql": "SELECT ..." }
```

### ERDC Optimizer — `POST {ERDC_BASE_URL}/optimise`

Request (`OptimiseRequest`):

```json
{ "budget_remaining": 80000, "objective": "maximise ROI", "account": "Tesco" }
```

Expected response:

```json
{ "currency": "GBP", "budget": 80000, "objective": "maximise ROI",
  "options": [ { "rank": 1, "mechanic": "Gondola end", "cost_gbp": 45000, "roi_predicted_pct": 167, ... } ],
  "selected_count": 1, "budget_used": 45000, "budget_utilisation_pct": 56.0 }
```

> The exact contract is **build-to-contract**: if the real services differ, the
> mapping lives entirely in `cdt.py` / `erdc.py` — no other code changes.

## Configuration

Set in `.env` (see [`.env.example`](../.env.example)). Empty base URL → mock.

| Variable | Default | Description |
|---|---|---|
| `CDT_BASE_URL` | _(empty)_ | CDT TextToSQL base URL; empty = mock |
| `CDT_API_KEY` | _(empty)_ | Bearer token for CDT |
| `CDT_TIMEOUT_S` | `30` | Request timeout (seconds) |
| `ERDC_BASE_URL` | _(empty)_ | ERDC Optimizer base URL; empty = mock |
| `ERDC_API_KEY` | _(empty)_ | Bearer token for ERDC |
| `ERDC_TIMEOUT_S` | `30` | Request timeout (seconds) |
| `TOOL_MAX_RETRIES` | `2` | Retries on transient HTTP failures |

Auth today is `Authorization: Bearer <key>`; Azure **managed identity** is the
intended production mechanism (see [architecture.md](architecture.md#8-azure-direction)).

## Error handling

`http.call_json` ([`http.py`](../src/app/tools/http.py)):

- Retries **transient failures** (network errors, 5xx) with linear backoff, up
  to `TOOL_MAX_RETRIES`.
- Does **not** retry client errors (4xx) — they won't succeed on retry.
- Raises a single `ToolError` on failure. The orchestrator catches it, logs
  `tool_failed`, and returns a safe "service unavailable" reply rather than a
  500 — it never invents data.

## Testing the live path locally (contract stubs)

A runnable stub implements both contracts so the **live HTTP path** can be
exercised before the real services exist:
[`integration_testing/tool_stubs.py`](../src/integration_testing/tool_stubs.py).

```bash
# terminal 1 — start the stub (distinctive figures so live calls are obvious)
uv run uvicorn integration_testing.tool_stubs:stub_app --port 8077

# terminal 2 — point the app at it and call the API for every intent
CDT_BASE_URL=http://127.0.0.1:8077 ERDC_BASE_URL=http://127.0.0.1:8077 \
    uv run python src/integration_testing/test.py
```

Verified end-to-end: the orchestrator POSTs the classifier-extracted params to
the stub (`CDT ← {account, question, sku, period}`, `ERDC ← {budget_remaining,
objective}`) and grounds its answer on the live response. The stub's distinctive
figures (188% / 167% ROI) appear in the answer, proving the live path rather than
the mock (142%).

## Test coverage

| Path | Where |
|---|---|
| Mock fallback (no URL) | `test_tools.py` + integration `test.py` |
| Live HTTP request/response | `test_tools.py` (patched `call_json`) + `tool_stubs.py` end-to-end |
| 4xx / transport errors → `ToolError` | `test_tools.py` |
| Orchestrator degradation on `ToolError` | `test_orchestrator.py` / wiring |
