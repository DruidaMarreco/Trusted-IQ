"""Pydantic models shared across API, agents, and tools."""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Incoming request payload for the orchestrator agent."""

    query: str = Field(..., description="User query to process")
    session_id: str | None = Field(default=None, description="Optional session identifier")
    account_scope: str | None = Field(
        default=None, description="Accounts the user covers, e.g. 'Tesco, Sainsbury's UK'"
    )
    planning_period: str | None = Field(default=None, description="Planning period context, e.g. 'FY2025 H1'")
    history: list[dict[str, str]] | None = Field(
        default=None, description="Prior conversation turns: [{'role': ..., 'content': ...}, ...]"
    )


class AgentResponse(BaseModel):
    """Response returned by the orchestrator agent."""

    result: str = Field(..., description="Final grounded answer")
    intent: str | None = Field(default=None, description="Classified intent")
    tool: str | None = Field(default=None, description="Tool the orchestrator routed to, if any")
    session_id: str | None = Field(default=None)
    metadata: dict[str, object] = Field(default_factory=dict)
