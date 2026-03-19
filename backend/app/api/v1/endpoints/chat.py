"""Chat endpoint for interacting with the agentic system."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import (
    get_or_create_session_context,
    get_orchestration_agent,
)
from app.models import AgentResponse, ChatApiResponse, ChatRequest
from app.utils.json_parser import parse_json_payload

router = APIRouter()

langfuse = get_client()

@router.post("")
@observe(name="chat_endpoint")
async def chat_endpoint(
    request: ChatRequest,
    session_id: Annotated[str, Query(alias="sessionId")],
) -> ChatApiResponse:
    """Run orchestration for the chat message within a user-owned session."""
    user_id = "dev-user"

    with propagate_attributes(
        session_id=session_id,
        metadata={
            "endpoint": "/api/v1/chat",
            "method": "POST",
        }
    ):
        try:
            context = get_or_create_session_context(session_id=session_id, user_id=user_id)
        except PermissionError as exc:
            langfuse.update_current_span(
                output={"error": "permission_denied", "reason": str(exc)}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

        try:
            orchestrator = get_orchestration_agent()
        except Exception as exc:
            langfuse.update_current_span(
                output={"error": "orchestrator_unavailable", "reason": str(exc)}
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Orchestration service unavailable: {exc}",
            ) from exc

        try:
            internal_response = await run_in_threadpool(
                orchestrator.orchestrate, request, context
            )
            result = ChatApiResponse(
                agent=internal_response.agent_name,
                payload=_extract_api_payload(internal_response),
            )
            langfuse.update_current_span(
                output={
                    "success": True,
                    "agent": internal_response.agent_name,
                    "response_length": len(str(result.payload)),
                }
            )
            return result
        except Exception as exc:
            langfuse.update_current_span(
                output={"error": "orchestration_failed", "reason": str(exc)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process chat request: {exc}",
            ) from exc


def _extract_api_payload(response: AgentResponse) -> dict[str, Any] | list[Any] | str:
    """Convert internal AgentResponse content into external API payload."""
    content = (response.content or "").strip()
    if not content:
        return {}

    parsed = _parse_json_payload(content)
    if parsed is not None:
        return parsed

    return content


def _parse_json_payload(content: str) -> dict[str, Any] | list[Any] | None:
    """Parse JSON payload from raw content or fenced markdown code block."""
    parsed = parse_json_payload(content, allow_array=True)
    if isinstance(parsed, (dict, list)):
        return parsed
    return None