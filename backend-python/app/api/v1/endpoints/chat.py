"""Chat endpoint for interacting with the agentic system."""

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.models import ChatRequest, AgentResponse

router = APIRouter()


@router.post("/", response_model=AgentResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
) -> AgentResponse:
    """
    Main chat endpoint for interacting with the agentic system.
    
    This endpoint will be implemented in Phase 5 with full agent orchestration.
    For now, it returns a placeholder response.
    
    Args:
        request: Chat request containing message
        current_user: Authenticated user from Firebase
        
    Returns:
        Response from the agentic system
    """
    return AgentResponse(
        agent_name="PlaceholderAgent",
        content=f"Received message: {request.message}",
        reasoning="This is a placeholder response until Phase 5 implementation",
        confidence_score=0.0,
        decision_trace=["placeholder", "pending_implementation"],
        sharp_metadata={"status": "placeholder", "user_id": current_user.get("uid")}
    )
