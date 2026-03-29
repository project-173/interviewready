"""Chat endpoint for interacting with the agentic system."""

import asyncio
import datetime as dt
import random
from typing import Annotated, Any
from app.core.config import settings
from fastapi import APIRouter, HTTPException, Query, status, Request
from fastapi.concurrency import run_in_threadpool
from app.core.limiter import limiter
from langfuse import get_client, observe, propagate_attributes

from app.api.v1.services import (
    get_or_create_session_context,
    get_orchestration_agent,
)
from app.agents import GeminiService
from app.agents.llm_judge import LLmasJudgeEvaluator
from app.models import AgentResponse, ChatApiResponse, ChatRequest
from app.utils.json_parser import parse_json_payload

router = APIRouter()

langfuse = get_client()

_llm_judge_evaluator = None


def get_llm_judge() -> LLmasJudgeEvaluator:
    """Get or create LLM-as-a-judge evaluator instance."""
    global _llm_judge_evaluator
    if _llm_judge_evaluator is None:
        gemini_service = GeminiService()
        _llm_judge_evaluator = LLmasJudgeEvaluator(gemini_service)
    return _llm_judge_evaluator


@router.post("")
@limiter.limit("10/minute")
@observe(name="chat_endpoint")
async def chat_endpoint(
    http_request: Request,
    request: ChatRequest,
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
                    orchestrator.orchestrate, request, context
                )

                if settings.LANGFUSE_LLM_AS_A_JUDGE_ENABLED and internal_response.content:
                    sample_rate = max(0.0, min(settings.EVAL_SAMPLE_RATE, 1.0))
                    if sample_rate > 0 and random.random() < sample_rate:
                        input_summary = (
                            "Intent: "
                            f"{request.intent}, "
                            "Job Description: "
                            f"{request.jobDescription[:200] if request.jobDescription else 'None'}"
                        )
                        current_trace = langfuse.get_current_trace()
                        trace_id = current_trace.id if current_trace else None
                        run_name = (
                            f"live/{internal_response.agent_name or 'unknown'}/"
                            f"{request.intent}/{dt.date.today().isoformat()}"
                        )

                        async def _run_judge_eval() -> None:
                            try:
                                judge = get_llm_judge()
                                await run_in_threadpool(
                                    judge.evaluate,
                                    agent_name=internal_response.agent_name or "unknown",
                                    input_data=input_summary,
                                    output=internal_response.content,
                                    trace_id=trace_id,
                                    intent=request.intent,
                                    session_id=session_id,
                                    message_history=request.messageHistory or [],
                                    run_name=run_name,
                                )
                            except Exception as judge_error:
                                import logging

                                logging.getLogger(__name__).warning(
                                    f"LLM-as-a-judge evaluation failed: {judge_error}"
                                )

                        asyncio.create_task(_run_judge_eval())

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
