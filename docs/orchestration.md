# Orchestration — thin (deterministic) vs agentic (model-driven)

The assistant ships **two orchestrators**. Both take a user query and return a
grounded answer using the right backend tool; they differ in **who decides which
tool to use**. We keep both because that decision is exactly what we want to
measure — two different ways.

| | Thin orchestrator | Agentic orchestrator |
|---|---|---|
| Class | `OrchestratorAgent` | `AgenticOrchestrator` |
| File | [`agents/orchestrator.py`](../src/app/agents/orchestrator.py) | [`agents/agentic_orchestrator.py`](../src/app/agents/agentic_orchestrator.py) |
| Tool decision | **Deterministic** Python router on the classified intent | **Model-driven** — Claude decides whether/which tool to call |
| LLM mechanism | 2 plain calls: classify (PROMPT-001), then ground (PROMPT-002) | Claude Agent SDK native tool-use loop |
| Tools exposed to the model? | No — the model only classifies | Yes — CDT/ERDC as in-process MCP tools |
| Backend | any provider (provider-uniform) | Claude Agent SDK (Claude Code subscription quota) |
| Measures | **intent-classification accuracy** | **tool-selection accuracy** |
| Role | **production** path (`POST /agent/invoke`) | capability test / future agentic features |

---

## 1. Thin orchestrator (production)

`classify intent (PROMPT-001) → route_to_tool() → ground (PROMPT-002)`.

The model's only judgement is the **intent label**; deterministic Python
([`tools/registry.py`](../src/app/tools/registry.py)) maps that label to a tool.
There is **no native tool-calling** — no tool schemas are sent to the model.

```python
raw, _ = await self._complete(INTENT_SYSTEM_PROMPT, classify_user)   # PROMPT-001
intent = parse_intent_json(raw)["intent"]
tool_name, desc, tool_output = await route_to_tool(intent, params, cfg, query=query)
answer, _ = await self._complete(RESPONSE_SYSTEM_PROMPT, respond_user) # PROMPT-002
```

Why this is the production default:

- **Provider-uniform** — native tool-calling APIs differ across OpenAI /
  Anthropic / Gemini / Azure; routing on a JSON intent label scores every model
  identically, with no per-provider glue. (This is why the model evaluation can
  compare models without special-casing.)
- **Deterministic & testable** — given an intent, the tool is fixed.
- **Grounding control** — PROMPT-002 is constrained to the returned
  `tool_output`; the figure-overlap groundedness check depends on that.

`CLARIFICATION` and `OUT_OF_SCOPE` resolve immediately (no tool). On a tool
failure the orchestrator catches `ToolError` and returns a safe reply.

The result (`OrchestratorResult`) carries the answer, intent, confidence, tool,
params, tool_output and per-turn `TurnMetrics` (latency, tokens, cost).

---

## 2. Agentic orchestrator (model decides)

Here Claude is **given the tools** (CDT/ERDC, as in-process Agent SDK MCP tools)
plus a system prompt, and **decides for itself** whether a tool is needed and
which to call — genuine native tool use, via the Claude Agent SDK's tool-use
loop, on the **subscription quota (no API key)**.

```python
server = create_sdk_mcp_server("tpo", tools=[text_to_sql_lookup, optimizer_run])
options = ClaudeAgentOptions(
    model="sonnet",
    system_prompt=AGENTIC_SYSTEM_PROMPT,
    mcp_servers={"tpo": server},
    allowed_tools=["mcp__tpo__text_to_sql_lookup", "mcp__tpo__optimizer_run"],
    permission_mode="bypassPermissions",
    setting_sources=[],          # isolate: don't load repo/user settings
)
async for message in query(prompt=user_query, options=options):
    ...  # capture ToolUseBlock(s) → which tools the agent chose
```

`AgenticResult.tool_names` reports the **TPO tools the agent invoked** (filtering
the SDK's built-in `ToolSearch` discovery step, which surfaces the deferred MCP
tools but is not a domain decision). The same in-process tools call the live or
mock CDT/ERDC backend, so this path benefits from the [tool layer](tools.md) too.

---

## 3. Tool-selection test & result

[`integration_testing/agentic_tool_test.py`](../src/integration_testing/agentic_tool_test.py)
runs scenarios through the agentic orchestrator and checks the tool the agent
**chose** against the expected one (or none), reporting tool-selection accuracy.

```bash
AGENTIC_MODEL=sonnet uv run python src/integration_testing/agentic_tool_test.py
```

Latest result (Sonnet) — **6/6 (100%)**:

| Scenario | Expected | Agent chose |
|---|---|---|
| "Why did you recommend the Easter display for Tesco?" | `text_to_sql_lookup` | `text_to_sql_lookup` ✅ |
| "List my top promos for Carrefour last quarter." | `text_to_sql_lookup` | `text_to_sql_lookup` ✅ |
| "Best promo options for my £80k budget at Tesco?" | `optimizer_run` | `optimizer_run` ✅ |
| "Re-optimise my Aldi plan to a 1.5× uplift guideline." | `optimizer_run` | `optimizer_run` ✅ |
| "Show me the options." | _(no tool)_ | none — asked one clarifying question ✅ |
| "What's the weather in London today?" | _(no tool)_ | none — declined ✅ |

> **Prompt-tuning finding.** An initial, over-cautious system prompt scored
> **4/6**: the agent asked for a SKU / budget instead of acting when an account
> was already named (and the optimizer has a default budget). Tuning the prompt
> to *prefer acting when it has enough to proceed* lifted it to 6/6. The "act vs
> over-clarify" threshold is exactly what this test is designed to catch.

---

## 4. When to use which

- **`POST /agent/invoke` uses the thin orchestrator** — deterministic, fast,
  provider-agnostic, fully unit-testable. This is production.
- **The agentic orchestrator** validates that a model can autonomously recognise
  it needs a tool and select the right one — the foundation for richer agentic
  features (multi-step tasks, tool chaining) and a second evaluation dimension.
  It currently requires the Claude Agent SDK backend.

See [ADR-0003](adr/0003-agentic-vs-thin-orchestrator.md) for the decision record.
