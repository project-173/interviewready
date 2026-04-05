"""Chat endpoint for interacting with the agentic system."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status, Request
from fastapi.concurrency import run_in_threadpool
from app.core.limiter import limiter
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import (
    get_or_create_session_context,
    get_orchestration_agent,
)
from langfuse import Langfuse, observe, propagate_attributes

langfuse = Langfuse()
from app.core.logging import logger
from app.models import AgentResponse, ChatApiResponse, ChatRequest
from app.utils.json_parser import parse_json_payload
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter()

langfuse = get_client()


@router.post("")
@limiter.limit(settings.DEFAULT_RATE_LIMIT)
@observe(name="chat_endpoint")
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    session_id: Annotated[str, Query(alias="sessionId")],
) -> ChatApiResponse:
    """Run orchestration for the chat message within a user-owned session."""
    user_id = "dev-user"

    with langfuse.start_as_current_observation(
        as_type="span",
        name="chat_api_request",
        metadata={
            "endpoint": "/api/v1/chat",
            "method": "POST",
        },
    ):
        with propagate_attributes(user_id=user_id, session_id=session_id):
            try:
                context = get_or_create_session_context(
                    session_id=session_id, user_id=user_id
                )
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
                    orchestrator.orchestrate, chat_request, context
                )
                payload = _extract_api_payload(internal_response)
                payload = _attach_payload_metadata(payload, internal_response)
                metadata = _extract_response_metadata(internal_response)
                result = ChatApiResponse(
                    agent=internal_response.agent_name,
                    payload=payload,
                    confidence_score=internal_response.confidence_score,
                    needs_review=internal_response.needs_review,
                    low_confidence_fields=internal_response.low_confidence_fields or [],
                    metadata=metadata,
                )
                langfuse.update_current_span(
                    output={
                        "success": True,
                        "agent": internal_response.agent_name,
                        "response_length": len(str(result.payload)),
                    }
                )
                return result
            except ValueError as exc:
                langfuse.update_current_span(
                    output={"error": "invalid_request", "reason": str(exc)}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
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
    try:
        parsed = parse_json_payload(content, allow_array=True)
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception as exc:
        logger.warning(f"Failed to parse JSON payload in chat endpoint: {exc}", content_preview=content[:100])
    return None


def _attach_payload_metadata(
    payload: dict[str, Any] | list[Any] | str,
    response: AgentResponse,
) -> dict[str, Any] | list[Any] | str:
    """Attach response metadata to payload when payload is a JSON object."""
    if not isinstance(payload, dict):
        return payload

    metadata = dict(payload.get("metadata") or {})
    metadata.update(
        {
            "confidence_score": response.confidence_score,
            "needs_review": response.needs_review,
            "low_confidence_fields": response.low_confidence_fields or [],
            "checkpoint_id": (response.sharp_metadata or {}).get("checkpoint_id"),
            "review_payload": (response.sharp_metadata or {}).get("review_payload"),
            "review_required": bool(response.needs_review),
        }
    )
    merged = dict(payload)
    merged["metadata"] = metadata
    return merged


def _extract_response_metadata(response: AgentResponse) -> dict[str, Any]:
    metadata = dict(response.sharp_metadata or {})
    metadata.update(
        {
            "confidence_score": response.confidence_score,
            "needs_review": response.needs_review,
            "low_confidence_fields": response.low_confidence_fields or [],
        }
    )
    return metadata
