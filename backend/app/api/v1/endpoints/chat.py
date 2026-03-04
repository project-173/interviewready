"""Chat endpoint for interacting with the agentic system."""

import json
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool

from app.api.v1.services import (
    get_or_create_session_context,
    get_orchestration_agent,
)
from app.core.auth import get_current_user
from app.models import AgentResponse, ChatApiResponse, ChatRequest

router = APIRouter()


@router.post("", response_model=ChatApiResponse)
async def chat_endpoint(
    request: ChatRequest,
    session_id: str = Query(..., alias="sessionId"),
    current_user: dict = Depends(get_current_user),
) -> ChatApiResponse:
    """Run orchestration for the chat message within a user-owned session."""
    user_id = str(
        current_user.get("uid")
        or current_user.get("user_id")
        or current_user.get("sub")
        or ""
    )
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user identity in authentication token",
        )

    try:
        context = get_or_create_session_context(session_id=session_id, user_id=user_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    try:
        orchestrator = get_orchestration_agent()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Orchestration service unavailable: {exc}",
        ) from exc

    try:
        internal_response = await run_in_threadpool(
            orchestrator.orchestrate, request, context
        )
        return ChatApiResponse(
            agent=internal_response.agent_name,
            payload=_extract_api_payload(internal_response),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {exc}",
        ) from exc


def _extract_api_payload(response: AgentResponse) -> Dict[str, Any] | list[Any] | str:
    """Convert internal AgentResponse content into external API payload."""
    content = (response.content or "").strip()
    if not content:
        return {}

    parsed = _parse_json_payload(content)
    if parsed is not None:
        return parsed

    return content


def _parse_json_payload(content: str) -> Dict[str, Any] | list[Any] | None:
    """Parse JSON payload from raw content or fenced markdown code block."""
    fenced_match = re.search(
        r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```",
        content,
        flags=re.IGNORECASE,
    )
    if fenced_match:
        json_text = fenced_match.group(1).strip()
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, (dict, list)):
                return parsed
        except json.JSONDecodeError:
            pass

    candidate_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", content)
    if not candidate_match:
        return None

    try:
        parsed = json.loads(candidate_match.group(1).strip())
        if isinstance(parsed, (dict, list)):
            return parsed
    except json.JSONDecodeError:
        return None

    return None
