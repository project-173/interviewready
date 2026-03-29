"""LLM-as-a-judge evaluator for agent outputs."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from langfuse import get_client

from app.core.config import settings
from app.core.logging import logger
from app.agents.eval_rubrics import JUDGE_TEMPERATURE, get_rubric


class JudgeEvaluation(BaseModel):
    """Evaluation result from LLM-as-a-judge."""

    quality_score: float  # 0-1 score for output quality
    accuracy_score: float  # 0-1 score for factual accuracy
    helpfulness_score: float  # 0-1 score for helpfulness
    reasoning: str  # Explanation of the evaluation
    concerns: list[str] = []  # Any issues identified


class LLmasJudgeEvaluator:
    """LLM-as-a-judge to evaluate agent outputs independently."""

    JUDGE_SYSTEM_PROMPT_BASE = """You are an expert evaluator of AI agent outputs.
Your task is to critically evaluate the quality of agent responses for a resume coaching application.

Evaluate on these dimensions:
1. Quality (0-1): Is the output well-structured, clear, and actionable?
2. Accuracy (0-1): Is the feedback factually correct and based on the resume content?
3. Helpfulness (0-1): Would this help a job seeker improve their resume?

Provide a JSON response with:
- quality_score: float (0-1)
- accuracy_score: float (0-1)
- helpfulness_score: float (0-1)
- reasoning: str (brief explanation)
- concerns: list[str] (any issues, empty if none)
"""

    def __init__(self, gemini_service: Any, *, temperature: float = JUDGE_TEMPERATURE):
        """Initialize with a Gemini service instance.

        Args:
            gemini_service: Service to use for judge LLM calls
            temperature: Gemini temperature for judge runs
        """
        self.gemini_service = gemini_service
        self.langfuse = get_client()
        self.temperature = temperature

    def evaluate(
        self,
        agent_name: str,
        input_data: str,
        output: str,
        expected_output: Optional[str] = None,
        trace_id: Optional[str] = None,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        message_history: Optional[List[Any]] = None,
        run_name: Optional[str] = None,
    ) -> JudgeEvaluation:
        """Evaluate an agent's output using LLM-as-a-judge.

        Args:
            agent_name: Name of the agent being evaluated
            input_data: The original input to the agent
            output: The agent's output to evaluate
            expected_output: Optional expected output for comparison
            trace_id: Optional Langfuse trace ID to attach scores to
            intent: Optional intent type for metadata
            session_id: Optional session ID for metadata

        Returns:
            JudgeEvaluation with scores and reasoning
        """
        logger.info(
            "Running LLM-as-a-judge evaluation",
            agent_name=agent_name,
            has_expected=expected_output is not None,
            intent=intent,
            session_id=session_id,
        )

        judge_input = self._build_judge_prompt(
            agent_name,
            input_data,
            output,
            expected_output,
            message_history=message_history,
        )
        system_prompt = self._build_system_prompt(agent_name)

        try:
            usage_details: Optional[Dict[str, int]] = None
            if hasattr(self.gemini_service, "generate_response_with_usage"):
                response, usage_details = self.gemini_service.generate_response_with_usage(
                    system_prompt=system_prompt,
                    user_input=judge_input,
                    context=None,
                    temperature=self.temperature,
                )
            else:
                response = self.gemini_service.generate_response(
                    system_prompt=system_prompt,
                    user_input=judge_input,
                    context=None,
                    temperature=self.temperature,
                )

            evaluation = self._parse_judge_response(response)

            if trace_id:
                self._log_scores_to_langfuse(
                    trace_id=trace_id,
                    agent_name=agent_name,
                    evaluation=evaluation,
                    intent=intent,
                    session_id=session_id,
                    run_name=run_name,
                )
                if usage_details:
                    self._log_usage_to_langfuse(
                        trace_id=trace_id,
                        agent_name=agent_name,
                        usage_details=usage_details,
                        system_prompt=system_prompt,
                        judge_input=judge_input,
                        response_text=response,
                        intent=intent,
                        session_id=session_id,
                        run_name=run_name,
                    )

            logger.info(
                "LLM-as-a-judge completed",
                agent_name=agent_name,
                quality=evaluation.quality_score,
                accuracy=evaluation.accuracy_score,
                helpfulness=evaluation.helpfulness_score,
            )

            return evaluation

        except Exception as e:
            logger.error(
                "LLM-as-a-judge evaluation failed", agent_name=agent_name, error=str(e)
            )
            return JudgeEvaluation(
                quality_score=0.5,
                accuracy_score=0.5,
                helpfulness_score=0.5,
                reasoning=f"Evaluation failed: {str(e)}",
                concerns=["Judge evaluation unavailable"],
            )

    def _build_system_prompt(self, agent_name: str) -> str:
        rubric = get_rubric(agent_name)
        return f"{self.JUDGE_SYSTEM_PROMPT_BASE}\nRUBRIC:\n{rubric}"

    def _build_judge_prompt(
        self,
        agent_name: str,
        input_data: str,
        output: str,
        expected_output: Optional[str],
        *,
        message_history: Optional[List[Any]] = None,
    ) -> str:
        """Build the prompt for the judge LLM."""
        prompt = f"""Evaluate the following agent output from '{agent_name}'.

AGENT INPUT:
{input_data[:2000]}

AGENT OUTPUT:
{output[:2000]}
"""
        if message_history:
            prompt += "\nMESSAGE HISTORY (most recent first):"
            for message in list(reversed(message_history))[:6]:
                if isinstance(message, dict):
                    role = message.get("role", "unknown")
                    text = message.get("text", "")
                else:
                    role = getattr(message, "role", "unknown")
                    text = getattr(message, "text", "")
                prompt += f"\n- {role}: {str(text)[:240]}"

        if expected_output:
            prompt += f"""
EXPECTED OUTPUT (for reference):
{expected_output[:1000]}
"""

        prompt += """
Provide your evaluation as valid JSON."""
        return prompt

    def _parse_judge_response(self, response: str) -> JudgeEvaluation:
        """Parse the judge's JSON response into a JudgeEvaluation."""
        import json
        from app.utils.json_parser import parse_json_object

        parsed = parse_json_object(response)

        if not parsed:
            return JudgeEvaluation(
                quality_score=0.5,
                accuracy_score=0.5,
                helpfulness_score=0.5,
                reasoning="Failed to parse judge response",
                concerns=["Parse error"],
            )

        return JudgeEvaluation(
            quality_score=float(parsed.get("quality_score", 0.5)),
            accuracy_score=float(parsed.get("accuracy_score", 0.5)),
            helpfulness_score=float(parsed.get("helpfulness_score", 0.5)),
            reasoning=parsed.get("reasoning", "No reasoning provided"),
            concerns=parsed.get("concerns", []),
        )

    def _build_cost_details(
        self, usage_details: Dict[str, int]
    ) -> Optional[Dict[str, float]]:
        prompt_rate = settings.JUDGE_PROMPT_COST_PER_1K_USD
        completion_rate = settings.JUDGE_COMPLETION_COST_PER_1K_USD
        if prompt_rate is None and completion_rate is None:
            return None

        cost_details: Dict[str, float] = {}
        total_cost = 0.0

        prompt_tokens = usage_details.get("prompt_tokens")
        completion_tokens = usage_details.get("completion_tokens")

        if prompt_rate is not None and prompt_tokens is not None:
            cost_details["prompt"] = (prompt_tokens / 1000.0) * prompt_rate
            total_cost += cost_details["prompt"]
        if completion_rate is not None and completion_tokens is not None:
            cost_details["completion"] = (completion_tokens / 1000.0) * completion_rate
            total_cost += cost_details["completion"]

        cost_details["total"] = total_cost
        return cost_details

    def _log_usage_to_langfuse(
        self,
        trace_id: str,
        agent_name: str,
        usage_details: Dict[str, int],
        system_prompt: str,
        judge_input: str,
        response_text: str,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        run_name: Optional[str] = None,
    ) -> None:
        if not usage_details:
            return

        metadata = {
            "agent": agent_name,
            "evaluator": "llm-as-a-judge",
        }
        if intent:
            metadata["intent"] = intent
        if session_id:
            metadata["session_id"] = session_id
        if run_name:
            metadata["run_name"] = run_name

        model_name = getattr(self.gemini_service, "model_name", None)
        cost_details = self._build_cost_details(usage_details)
        input_payload = {
            "system_prompt": system_prompt[:2000],
            "user_prompt": judge_input[:4000],
        }
        output_payload = (response_text or "")[:4000]

        try:
            current_trace_id = self.langfuse.get_current_trace_id()
        except Exception:
            current_trace_id = None

        if current_trace_id == trace_id:
            try:
                generation_metadata = {
                    **metadata,
                    "usage_details": usage_details,
                }
                if cost_details is not None:
                    generation_metadata["cost_details"] = cost_details

                self.langfuse.update_current_generation(
                    name="llm_judge",
                    input=input_payload,
                    output=output_payload,
                    metadata=generation_metadata,
                    model=model_name,
                    usage_details=usage_details,
                    cost_details=cost_details,
                )
                return
            except Exception as e:
                logger.warning(
                    "Failed to update judge generation usage in Langfuse",
                    error=str(e),
                    trace_id=trace_id,
                )

        try:
            event_metadata: Dict[str, Any] = {
                **metadata,
                "usage_details": usage_details,
            }
            if cost_details is not None:
                event_metadata["cost_details"] = cost_details
            if model_name:
                event_metadata["model"] = model_name

            self.langfuse.create_event(
                trace_context={"trace_id": trace_id},
                name="llm_judge_generation",
                input=input_payload,
                output=output_payload,
                metadata=event_metadata,
            )
        except Exception as e:
            logger.warning(
                "Failed to log judge usage to Langfuse",
                error=str(e),
                trace_id=trace_id,
            )

    def _log_scores_to_langfuse(
        self,
        trace_id: str,
        agent_name: str,
        evaluation: JudgeEvaluation,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
        run_name: Optional[str] = None,
    ) -> None:
        """Log evaluation scores to Langfuse."""
        try:
            # Build metadata with all available context
            metadata = {
                "agent": agent_name,
                "evaluator": "llm-as-a-judge",
            }
            if intent:
                metadata["intent"] = intent
            if session_id:
                metadata["session_id"] = session_id
            if run_name:
                metadata["run_name"] = run_name
            
            self.langfuse.create_score(
                name="judge_quality_score",
                value=evaluation.quality_score,
                trace_id=trace_id,
                metadata=metadata,
            )
            self.langfuse.create_score(
                name="judge_accuracy_score",
                value=evaluation.accuracy_score,
                trace_id=trace_id,
                metadata=metadata,
            )
            self.langfuse.create_score(
                name="judge_helpfulness_score",
                value=evaluation.helpfulness_score,
                trace_id=trace_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(
                "Failed to log judge scores to Langfuse",
                error=str(e),
                trace_id=trace_id,
            )
