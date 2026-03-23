"""LLM-as-a-judge evaluator for agent outputs."""

from typing import Optional, Dict, Any
from pydantic import BaseModel
from langfuse import get_client

from app.core.logging import logger


class JudgeEvaluation(BaseModel):
    """Evaluation result from LLM-as-a-judge."""

    quality_score: float  # 0-1 score for output quality
    accuracy_score: float  # 0-1 score for factual accuracy
    helpfulness_score: float  # 0-1 score for helpfulness
    reasoning: str  # Explanation of the evaluation
    concerns: list[str] = []  # Any issues identified


class LLmasJudgeEvaluator:
    """LLM-as-a-judge to evaluate agent outputs independently."""

    JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of AI agent outputs. 
Your task is to critically evaluate the quality of agent responses for a resume coaching application.

Evaluate on these dimensions:
1. **Quality** (0-1): Is the output well-structured, clear, and actionable?
2. **Accuracy** (0-1): Is the feedback factually correct and based on the resume content?
3. **Helpfulness** (0-1): Would this help a job seeker improve their resume?

Provide a JSON response with:
- quality_score: float (0-1)
- accuracy_score: float (0-1)  
- helpfulness_score: float (0-1)
- reasoning: str (brief explanation)
- concerns: list[str] (any issues, empty if none)"""

    def __init__(self, gemini_service: Any):
        """Initialize with a Gemini service instance.

        Args:
            gemini_service: Service to use for judge LLM calls
        """
        self.gemini_service = gemini_service
        self.langfuse = get_client()

    def evaluate(
        self,
        agent_name: str,
        input_data: str,
        output: str,
        expected_output: Optional[str] = None,
        trace_id: Optional[str] = None,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
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
            agent_name, input_data, output, expected_output
        )

        try:
            response = self.gemini_service.generate_response(
                system_prompt=self.JUDGE_SYSTEM_PROMPT,
                user_input=judge_input,
                context=None,
            )

            evaluation = self._parse_judge_response(response)

            if trace_id:
                self._log_scores_to_langfuse(
                    trace_id=trace_id,
                    agent_name=agent_name,
                    evaluation=evaluation,
                    intent=intent,
                    session_id=session_id,
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

    def _build_judge_prompt(
        self,
        agent_name: str,
        input_data: str,
        output: str,
        expected_output: Optional[str],
    ) -> str:
        """Build the prompt for the judge LLM."""
        prompt = f"""Evaluate the following agent output from '{agent_name}'.

AGENT INPUT:
{input_data[:2000]}

AGENT OUTPUT:
{output[:2000]}
"""

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

    def _log_scores_to_langfuse(
        self,
        trace_id: str,
        agent_name: str,
        evaluation: JudgeEvaluation,
        intent: Optional[str] = None,
        session_id: Optional[str] = None,
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
