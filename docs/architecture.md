# Architecture — TradeIQ GenAI Sales Assistant

## Pattern: thin orchestrator (orchestrator–workers, minimal)

A single LLM (Azure OpenAI GPT-4o in production; any provider via the factory)
performs **intent classification** and routes the query to exactly one tool, then
a second prompt generates a **grounded** natural-language answer from that tool's
output. There is deliberately **no multi-agent system and no RAG** — grounding
comes from structured tool output, not retrieval (see ADR-0002 / the Gate-2
solution design).

```
user query
   │
   ▼
Intent Classifier  (src/app/prompts.py : INTENT_SYSTEM_PROMPT, PROMPT-001)
   │  → { intent, confidence, extracted_params, clarifying_question }
   ▼
route_to_tool()    (src/app/tpo_tools.py)
   ├─ DATA_QUERY     → text_to_sql_lookup   (CDT TextToSQL agent over SQL MI)
   ├─ OPTIMIZER_RUN  → optimizer_run        (ERDC Optimizer API)
   ├─ CLARIFICATION  → ask one follow-up question
   └─ OUT_OF_SCOPE   → politely decline
   │  → tool_output (JSON: rows / ranked options)
   ▼
Response Generator (src/app/prompts.py : RESPONSE_SYSTEM_PROMPT, PROMPT-002)
   │  → grounded business answer (ROI, uplift, incremental volume)
   ▼
answer
```

## Intents

| Intent | Meaning | Routes to |
|--------|---------|-----------|
| `DATA_QUERY` | Retrieve/understand existing data ("why was X recommended?", "top promos last quarter") | CDT TextToSQL agent |
| `OPTIMIZER_RUN` | Generate new options / re-optimise ("best options for £50k", "optimise for volume") | ERDC Optimizer API |
| `CLARIFICATION` | Ambiguous / missing parameters | Ask one follow-up |
| `OUT_OF_SCOPE` | Not about trade promotion | Decline |

The classifier also extracts parameters: `account`, `time_period`,
`budget_remaining`, `objective`, `sku`.

## Groundedness

The Response Generator must use **only** the `tool_output` and never fabricate
figures. Groundedness is the headline quality metric in the model evaluation
([docs/model-evaluation.md](model-evaluation.md)), measured two ways: an LLM
rubric and a deterministic figure-overlap check (every number in the answer must
appear in the tool output).

## Code map (`src/app/`)

| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI app factory; wires LLMs → orchestrator → routes |
| `config.py` | `pydantic-settings` configuration (provider, models, proxy) |
| `llm_factory.py` | `build_llm()` — provider-agnostic chat model (Azure/OpenAI/Anthropic/Ollama, Claude Code, or an OpenAI-compatible proxy) |
| `claude_code_llm.py` | `ChatClaudeCode` — LangChain model backed by the Claude Agent SDK (subscription quota) |
| `prompts.py` | Canonical PROMPT-001 (intent) and PROMPT-002 (response) |
| `tpo_tools.py` | Mock CDT TextToSQL + ERDC Optimizer tools over synthetic data |
| `eval.py` | Pure helpers: intent parsing + groundedness figure-overlap |
| `api/routes.py` | `/agent/invoke` endpoint |
| `schemas/models.py` | Request/response models |
| `logging.py` | Structured logging + correlation IDs |

## Provider flexibility

`build_llm()` selects the backend at runtime:
- Native providers (`azure_openai`, `openai`, `anthropic`, `ollama`)
- `claude_code` — runs through Claude Code on the subscription quota
- A unified **OpenAI-compatible proxy** when `LLM_PROXY_BASE_URL` is set (all
  models routed through one gateway, e.g. LiteLLM)

This is what lets the model-evaluation harness compare models without code
changes.
