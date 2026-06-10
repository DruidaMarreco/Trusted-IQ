"""Orchestrator agent.

Receives the user query, decides which subagents/tools to invoke,
aggregates results, and returns a final response.
"""
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from app.agents.subagent_a import SubagentA
from app.agents.subagent_b import SubagentB
from app.config import settings
from app.tools.sample_tool import sample_tool


SYSTEM_PROMPT = """You are a senior orchestrator agent.
You have access to tools and two specialised subagents (A and B).
Decompose the user request, delegate to the right resource, and synthesise a final answer.
"""


class OrchestratorAgent:
    """Top-level agent that coordinates subagents and tools."""

    def __init__(
        self,
        llm: BaseChatModel,
        subagent_a: SubagentA,
        subagent_b: SubagentB,
    ) -> None:
        self._subagent_a = subagent_a
        self._subagent_b = subagent_b

        self._agent = create_agent(
            model=llm,
            tools=[sample_tool],
            system_prompt=SYSTEM_PROMPT,
            debug=settings.debug,
        )

    async def run(self, query: str) -> str:
        """Orchestrate subagents/tools and return final answer."""
        result_a = await self._subagent_a.run(query)
        result_b = await self._subagent_b.run(query)

        enriched_input = (
            f"{query}\n\n[SubagentA context]: {result_a}\n[SubagentB context]: {result_b}"
        )
        output = await self._agent.ainvoke({"messages": [{"role": "user", "content": enriched_input}]})
        messages = output.get("messages", [])
        return str(messages[-1].content) if messages else ""
