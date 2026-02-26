"""Agents endpoint for listing available agents."""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from app.core.auth import get_current_user

router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information model."""
    
    name: str
    description: str
    status: str


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[AgentInfo]:
    """
    List all available agents and their system prompts.
    
    This endpoint will be implemented in Phase 5 with actual agent information.
    For now, it returns placeholder agent data.
    
    Args:
        current_user: Authenticated user from Firebase
        
    Returns:
        List of available agents with their metadata
    """
    return [
        AgentInfo(
            name="ExtractorAgent",
            description="Parses and extracts structured information from resumes",
            status="pending_implementation"
        ),
        AgentInfo(
            name="ResumeCriticAgent", 
            description="Analyzes resume quality and provides improvement suggestions",
            status="pending_implementation"
        ),
        AgentInfo(
            name="ContentStrengthAgent",
            description="Evaluates content strength and impact of resume sections",
            status="pending_implementation"
        ),
        AgentInfo(
            name="JobAlignmentAgent",
            description="Assesses alignment between resume and job requirements",
            status="pending_implementation"
        ),
        AgentInfo(
            name="InterviewCoachAgent",
            description="Provides interview coaching and preparation guidance",
            status="pending_implementation"
        )
    ]
