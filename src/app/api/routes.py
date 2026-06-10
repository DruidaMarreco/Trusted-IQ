"""FastAPI router — agent endpoints."""

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import OrchestratorAgent
from app.schemas.models import AgentRequest, AgentResponse

router = APIRouter(prefix="/agent", tags=["agent"])

# Injected by create_app() at startup — do not instantiate here.
_orchestrator: OrchestratorAgent | None = None


def set_orchestrator(orchestrator: OrchestratorAgent) -> None:
    """Wire the orchestrator instance (called from app factory)."""
    global _orchestrator
    _orchestrator = orchestrator


@router.post("/invoke", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest) -> AgentResponse:
    """Invoke the orchestrator agent with a user query."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised")
    try:
        result = await _orchestrator.run(request.query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentResponse(
        result=result.answer,
        intent=result.intent,
        tool=result.tool,
        session_id=request.session_id,
        metadata={"confidence": result.confidence, "params": result.params},
    )
