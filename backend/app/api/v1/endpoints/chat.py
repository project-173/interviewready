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
from app.api.v1.response_transformers import agent_response_to_api, enrich_agent_response_for_user
from langfuse import Langfuse, observe, propagate_attributes

langfuse = Langfuse()
from app.models import AgentResponse, ChatApiResponse, ChatRequest
from app.utils.json_parser import parse_json_payload
from app.core.limiter import limiter
from app.core.config import settings
from app.core.logging import logger

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
                
                # Enrich response with user-facing explanations
                enriched_response = enrich_agent_response_for_user(internal_response)
                
                # Transform to user-facing API response with transparency fields
                api_response = agent_response_to_api(enriched_response, include_sharp_metadata=False)
                
                # Build final response with transparency fields
                result = ChatApiResponse(
                    agent=api_response.agent,
                    payload=api_response.payload,
                    confidence_score=api_response.confidence_score,
                    confidence_explanation=api_response.confidence_explanation,
                    reasoning=api_response.reasoning,
                    improvement_suggestions=api_response.improvement_suggestions,
                    needs_review=api_response.needs_review,
                    low_confidence_fields=api_response.low_confidence_fields,
                    # Bias & Governance transparency
                    bias_flags=api_response.bias_flags,
                    bias_severity=api_response.bias_severity,
                    bias_description=api_response.bias_description,
                    governance_audit_status=api_response.governance_audit_status,
                    governance_flags=api_response.governance_flags,
                    requires_human_review=api_response.requires_human_review,
                    # Interview-specific
                    answer_score=api_response.answer_score,
                    can_proceed=api_response.can_proceed,
                    next_challenge=api_response.next_challenge,
                )
                
                langfuse.update_current_span(
                    output={
                        "success": True,
                        "agent": internal_response.agent_name,
                        "response_length": len(str(result.payload)),
                        "confidence_score": api_response.confidence_score,
                        "bias_flags_count": len(api_response.bias_flags),
                        "governance_flags": api_response.governance_flags,
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
        }
    )
    merged = dict(payload)
    merged["metadata"] = metadata
    return merged
