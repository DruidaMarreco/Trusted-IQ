"""Pydantic models shared across API, agents, and tools."""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Incoming request payload for the orchestrator agent."""

    query: str = Field(..., description="User query to process")
    session_id: str | None = Field(default=None, description="Optional session identifier")


class AgentResponse(BaseModel):
    """Response returned by the orchestrator agent."""

    result: str = Field(..., description="Final agent output")
    session_id: str | None = Field(default=None)
    metadata: dict[str, object] = Field(default_factory=dict)
