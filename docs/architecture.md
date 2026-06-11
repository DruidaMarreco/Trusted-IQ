# Architecture — TradeIQ GenAI Sales Assistant

The TradeIQ Sales Assistant is the **conversational layer** over a proven Trade
Promotion Optimisation (TPO) platform. Commercial users (Key Account Managers,
Trade Marketing Managers, Commercial Directors) ask, in plain language, *why* a
promotion was recommended or *what* the best options are for a remaining budget;
the assistant routes the question to the right backend tool and returns a
**grounded** business answer.

This document covers the end-to-end design: the orchestration pattern (and the
two implementations we test), the tool-integration layer, grounding, provider
flexibility, and the code map.

---

## 1. Pattern: thin orchestrator (orchestrator–workers, minimal)

A single LLM performs **intent classification** and routes the query to exactly
one tool, then a second prompt generates a **grounded** natural-language answer
from that tool's output. There is deliberately **no multi-agent system and no
RAG** — grounding comes from structured tool output, not retrieval
(see [ADR-0002](adr/0002-langchain-provider-agnostic-factory.md) and the Gate-2
solution design).

```
user query
   │
   ▼
Intent Classifier  (src/app/prompts.py : INTENT_SYSTEM_PROMPT, PROMPT-001)
   │  → { intent, confidence, extracted_params, clarifying_question }
   ▼
route_to_tool()    (src/app/tools/)
   ├─ DATA_QUERY     → CDT TextToSQL agent over SQL MI   (live HTTP or mock fallback)
   ├─ OPTIMIZER_RUN  → ERDC Optimizer API                (live HTTP or mock fallback)
   ├─ CLARIFICATION  → ask one follow-up question
   └─ OUT_OF_SCOPE   → politely decline
   │  → tool_output (JSON: rows / ranked options)
   ▼
Response Generator (src/app/prompts.py : RESPONSE_SYSTEM_PROMPT, PROMPT-002)
   │  → grounded business answer (ROI, uplift, incremental volume)
   ▼
answer
```

### Intents

| Intent | Meaning | Routes to |
|--------|---------|-----------|
| `DATA_QUERY` | Retrieve/understand existing data ("why was X recommended?", "top promos last quarter") | CDT TextToSQL agent |
| `OPTIMIZER_RUN` | Generate new options / re-optimise ("best options for £50k", "optimise for volume") | ERDC Optimizer API |
| `CLARIFICATION` | Ambiguous / missing parameters | Ask one follow-up |
| `OUT_OF_SCOPE` | Not about trade promotion | Decline |

The classifier also extracts parameters: `account`, `time_period`,
`budget_remaining`, `objective`, `sku`.

---

## 2. Two orchestrators (and why we test both)

The service ships **two** orchestrator implementations. They solve the same
problem — get the user a grounded answer using the right tool — but differ in
*who decides which tool to use*. Keeping both lets us measure that decision two
ways. See [orchestration.md](orchestration.md) for the full comparison.

| | Thin orchestrator | Agentic orchestrator |
|---|---|---|
| Class | `OrchestratorAgent` ([agents/orchestrator.py](../src/app/agents/orchestrator.py)) | `AgenticOrchestrator` ([agents/agentic_orchestrator.py](../src/app/agents/agentic_orchestrator.py)) |
| Tool decision | **Deterministic** — Python router maps the classified intent → tool | **Model-driven** — Claude is given the tools and *decides* whether/which to call (native tool use) |
| Mechanism | two plain LLM calls (classify, then ground) + `route_to_tool` | Claude Agent SDK tool-use loop with in-process MCP tools |
| Backend | any provider (provider-uniform) | Claude Agent SDK (Claude Code subscription quota) |
| What it measures | **intent-classification accuracy** | **tool-selection accuracy** |
| Used by | `POST /agent/invoke` (production path) | tool-use evaluation / future agentic features |

The thin orchestrator is the **production** path: deterministic, testable,
provider-agnostic. The agentic orchestrator validates that a model can *itself*
recognise it needs a tool and pick the right one — the seed of richer agentic
behaviour. Both ground their final answer the same way (PROMPT-002 over
`tool_output`).

---

## 3. Tool integration layer (`src/app/tools/`)

Two external systems back the tool-using intents. Each tool calls its **live**
service over HTTP when configured, and otherwise falls back to **deterministic
mock** output, so local dev, unit tests and the model evaluation run with no
external dependencies. Full detail: [tools.md](tools.md).

```
route_to_tool(intent, params, cfg, query)        registry.py
   ├─ DATA_QUERY     → cdt.text_to_sql_lookup()   cdt.py   → CDT_BASE_URL set? live HTTP : mock
   └─ OPTIMIZER_RUN  → erdc.optimizer_run()        erdc.py  → ERDC_BASE_URL set? live HTTP : mock
                                                    http.py  → shared async client (retries, ToolError)
                                                    mock.py  → synthetic, deterministic data
```

- **Live or mock per tool**, selected by `CDT_BASE_URL` / `ERDC_BASE_URL`. No
  code change to go live — only configuration.
- **Thin-orchestrator boundary:** CDT owns NL→SQL generation and SQL MI access;
  the orchestrator holds **no database credentials**.
- **Graceful degradation:** a failed live call raises `ToolError`, which the
  orchestrator catches and answers safely (never fabricates).

---

## 4. Groundedness

The Response Generator must use **only** the `tool_output` and never fabricate
figures. Groundedness is the headline quality metric in the model evaluation
([model-evaluation.md](model-evaluation.md)), measured two ways: an LLM rubric
and a deterministic figure-overlap check (every number in the answer must appear
in the tool output).

---

## 5. Provider flexibility

`build_llm()` ([llm_factory.py](../src/app/llm_factory.py)) selects the backend
at runtime:

- Native providers (`azure_openai`, `openai`, `anthropic`, `ollama`)
- `claude_code` — runs through Claude Code on the subscription quota
  ([claude_code_llm.py](../src/app/claude_code_llm.py))
- A unified **OpenAI-compatible proxy** when `LLM_PROXY_BASE_URL` is set (all
  models routed through one gateway, e.g. LiteLLM)

This is what lets the model-evaluation harness compare models without code
changes, and what keeps the thin orchestrator provider-agnostic.

---

## 6. API surface (`src/app/api/routes.py`)

| Endpoint | Purpose |
|---|---|
| `GET /livez` | Liveness probe (no LLM) |
| `GET /readyz` | Readiness probe + version |
| `POST /agent/invoke` | Run the orchestrator on a query |

`POST /agent/invoke` accepts `query` plus optional `session_id`, `account_scope`,
`planning_period` and `history` (prior turns), and returns the grounded `result`,
the classified `intent`, the `tool` used, and `metadata` carrying confidence,
extracted params and per-turn usage `metrics` (latency, tokens, estimated cost).

---

## 7. Code map (`src/app/`)

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app factory; wires LLM → orchestrator → routes; health probes; correlation-ID middleware |
| `config.py` | `pydantic-settings` configuration (provider, models, proxy, tool backends) |
| `llm_factory.py` | `build_llm()` — provider-agnostic chat model (Azure/OpenAI/Anthropic/Ollama, Claude Code, or an OpenAI-compatible proxy) |
| `claude_code_llm.py` | `ChatClaudeCode` — LangChain model backed by the Claude Agent SDK (subscription quota) |
| `prompts.py` | Canonical PROMPT-001 (intent) and PROMPT-002 (response) |
| `agents/orchestrator.py` | `OrchestratorAgent` — the thin orchestrator (classify → route → ground) |
| `agents/agentic_orchestrator.py` | `AgenticOrchestrator` — model-driven tool use via the Agent SDK |
| `tools/` | CDT TextToSQL + ERDC Optimizer integrations — `registry.py` (routing), `cdt.py`/`erdc.py` (live-or-mock), `http.py` (async client + `ToolError`), `mock.py` (synthetic data) |
| `eval.py` | Pure helpers: intent parsing + groundedness figure-overlap |
| `metrics.py` | `estimate_cost`, `CallMetrics`, `TurnMetrics` — per-call/per-turn usage tracking |
| `api/routes.py` | `/agent/invoke` endpoint + orchestrator wiring |
| `schemas/models.py` | Request/response models (`AgentRequest`, `AgentResponse`) |
| `logging.py` | Structured logging + correlation IDs |

---

## 8. Azure direction

The service is built provider-agnostic with Azure as the production target:
`build_llm()` supports `azure_openai`; the tool layer expects the live CDT/ERDC
services (with `Bearer` auth today, managed identity to follow); a `Dockerfile`
targets AKS / Container Apps with health probes. Secrets (tool API keys, model
keys) are designed to come from Key Vault / environment, never the repo.
