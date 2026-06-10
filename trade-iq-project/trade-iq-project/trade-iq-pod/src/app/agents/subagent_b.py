"""Subagent B — specialised subtask handler.

Receives delegated work from the orchestrator.
Replace stub logic with real chain / retriever / tool calls.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


class SubagentB:
    """Handles domain-specific subtask B."""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def run(self, task: str) -> str:
        """Execute subtask and return result string."""
        # TODO: replace with real chain / prompt template
        response = await self._llm.ainvoke([HumanMessage(content=f"[SubagentB] {task}")])
        return str(response.content)
