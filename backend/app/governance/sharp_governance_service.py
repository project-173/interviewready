"""SHARP governance service ported from Java implementation.

Now integrated with AI-based bias detection, hallucination evaluation,
and explainability services for more robust governance.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

try:
    from langfuse import Langfuse
except ImportError:  # pragma: no cover
    class _NoopLangfuse:
        def update_current_span(self, *args: Any, **kwargs: Any) -> None:
            return None

    Langfuse = _NoopLangfuse

from app.core.config import settings
from app.models.agent import AgentResponse
from app.governance.bias_detection_service import BiasDetectionService
from app.governance.hallucination_evaluation_service import (
    HallucinationEvaluationService,
)
from app.governance.explainability_service import ExplainabilityService

langfuse = Langfuse()


class GovernanceFieldNames:
    GOVERNANCE = "governance"
    AUDIT = "governance_audit"
    TIMESTAMP = "audit_timestamp"
    AUDIT_FLAGS = "audit_flags"
    HALLUCINATION_CHECK_PASSED = "hallucination_check_passed"
    CONFIDENCE_CHECK_PASSED = "confidence_check_passed"
    HALLUCINATION_RISK = "hallucinationRisk"
    UNFAITHFUL_SUGGESTIONS = "unfaithful_suggestions"
    TOTAL_SUGGESTIONS = "total_suggestions"
    HAS_QUANTIFIED_ACHIEVEMENTS = "has_quantified_achievements"
    HIGH_EVIDENCE_SKILLS_COUNT = "high_evidence_skills_count"
    CONTENT_PARSE_ERROR = "content_parse_error"
    VALIDATION_ERROR = "validation_error"


class GovernanceAuditStatus:
    PASSED = "passed"
    FLAGGED = "flagged"


class GovernanceFlags:
    LOW_CONFIDENCE = "low_confidence"
    HALLUCINATION_RISK = "hallucination_risk"
    UNFAITHFUL_SUGGESTIONS = "unfaithful_suggestions"
    SENSITIVE_INTERVIEW_CONTENT = "sensitive_interview_content"
    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"
    BIAS_REVIEW_REQUIRED = "bias_review_required"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class SharpGovernanceService:
    """Audit and risk evaluation service for agent responses.

    Now integrated with AI-based services for more robust bias detection,
    hallucination evaluation, and explainability.
    """

    def __init__(self) -> None:
        self._agent_validators: dict[
            str,
            Callable[[AgentResponse, dict[str, Any], str | None], None],
        ] = {
            "ContentStrengthAgent": self._validate_content_strength_agent,
            "InterviewCoachAgent": self._validate_interview_coach_agent,
        }
        # Initialize AI-based governance services
        self.bias_detector = BiasDetectionService()
        self.hallucination_evaluator = HallucinationEvaluationService()
        self.explainability_service = ExplainabilityService()

    def audit(
        self,
        response: AgentResponse,
        original_input: str | None = None,
    ) -> AgentResponse:
        """Audit response and attach governance metadata using AI services."""
        metadata = dict(response.sharp_metadata or {})
        self._ensure_governance_container(metadata)

        self._set_governance_field(
            metadata,
            GovernanceFieldNames.AUDIT,
            GovernanceAuditStatus.PASSED,
        )
        self._set_governance_field(
            metadata,
            GovernanceFieldNames.TIMESTAMP,
            int(time.time() * 1000),
        )

        # Use AI-based hallucination evaluation
        hallucination_check = self._check_hallucination(response, original_input)
        self._set_governance_field(
            metadata,
            GovernanceFieldNames.HALLUCINATION_CHECK_PASSED,
            hallucination_check,
        )

        # Use AI-based bias detection
        bias_result = self._check_bias(response, original_input)
        metadata["bias_check"] = bias_result

        confidence_check = self._check_confidence_threshold(response)
        self._set_governance_field(
            metadata,
            GovernanceFieldNames.CONFIDENCE_CHECK_PASSED,
            confidence_check,
        )

        # Generate explainability insights
        explanation = self._generate_decision_explanation(response, original_input)
        metadata["explainability"] = explanation

        validator = self._agent_validators.get(response.agent_name or "")
        if validator:
            validator(response, metadata, original_input)

        flags: list[str] = []
        if not hallucination_check:
            flags.append(GovernanceFlags.HALLUCINATION_RISK)
        if not confidence_check:
            flags.append(GovernanceFlags.LOW_CONFIDENCE)
        if bias_result.get("risk_score", 0.0) > 0.6:
            flags.append(GovernanceFlags.BIAS_REVIEW_REQUIRED)

        if flags:
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.AUDIT,
                GovernanceAuditStatus.FLAGGED,
            )
            for flag in flags:
                self._append_flag(metadata, flag)

        response.sharp_metadata = metadata
        self._publish_governance_trace(metadata)
        return response

    def _ensure_governance_container(self, metadata: dict[str, Any]) -> dict[str, Any]:
        container = metadata.get(GovernanceFieldNames.GOVERNANCE)
        if not isinstance(container, dict):
            container = {}
            metadata[GovernanceFieldNames.GOVERNANCE] = container
        return container

    def _set_governance_field(
        self,
        metadata: dict[str, Any],
        field_name: str,
        value: Any,
    ) -> None:
        metadata[field_name] = value
        container = self._ensure_governance_container(metadata)
        container[field_name] = value

    def _append_flag(self, metadata: dict[str, Any], flag: str) -> None:
        flags = list(metadata.get(GovernanceFieldNames.AUDIT_FLAGS, []))
        if flag not in flags:
            flags.append(flag)
        self._set_governance_field(metadata, GovernanceFieldNames.AUDIT_FLAGS, flags)

    def _publish_governance_trace(self, metadata: dict[str, Any]) -> None:
        try:
            langfuse.update_current_span(
                metadata={
                    GovernanceFieldNames.GOVERNANCE: metadata[
                        GovernanceFieldNames.GOVERNANCE
                    ]
                }
            )
        except Exception:
            pass

    def _check_bias(
        self,
        response: AgentResponse,
        original_input: str | None,
    ) -> dict[str, Any]:
        """Check for bias signals using AI-based detection."""
        if not response.content:
            return {"risk_score": 0.0, "bias_signals": []}

        # Scan response content for bias
        response_bias = self.bias_detector.scan(response.content or "", context="response")

        # If we have original input (e.g., job description), also scan that
        input_bias = {}
        if original_input:
            input_bias = self.bias_detector.scan(original_input, context="input")

        # Combine results
        result = {
            "response_bias": response_bias,
            "input_bias": input_bias,
            "risk_score": max(
                response_bias.get("risk_score", 0.0),
                input_bias.get("risk_score", 0.0),
            ),
            "protected_attributes": list(
                set(
                    response_bias.get("protected_attributes_found", [])
                    + input_bias.get("protected_attributes_found", [])
                )
            ),
            "bias_signals": list(
                set(
                    response_bias.get("bias_signals_detected", [])
                    + input_bias.get("bias_signals_detected", [])
                )
            ),
        }
        return result

    def _generate_decision_explanation(
        self,
        response: AgentResponse,
        original_input: str | None,
    ) -> dict[str, Any]:
        """Generate explainability insights for the decision."""
        context = {}
        if original_input:
            context["input"] = original_input[:500]  # Truncate for safety
        if response.reasoning:
            context["reasoning"] = response.reasoning

        # Use explainability service to attribute decision
        explanation = self.explainability_service.attribute_decision(
            decision_output=response.content or "",
            input_context=context,
            agent_name=response.agent_name,
        )

        # Also generate a human-readable explanation
        readable_explanation = self.explainability_service.generate_explanation(
            decision=response.content or "",
            attributions=explanation.get("attributions", []),
            agent_name=response.agent_name,
            audience="reviewer",
        )

        return {
            "attribution": explanation,
            "explanation": readable_explanation,
            "transparency_score": explanation.get("transparency_score", 0.0),
        }

    def _publish_governance_trace(self, metadata: dict[str, Any]) -> None:
        try:
            langfuse.update_current_span(
                metadata={
                    GovernanceFieldNames.GOVERNANCE: metadata[
                        GovernanceFieldNames.GOVERNANCE
                    ]
                }
            )
        except Exception:
            pass

    def _validate_interview_coach_agent(
        self,
        response: AgentResponse,
        metadata: dict[str, Any],
        original_input: str | None = None,
    ) -> None:
        """Apply interview-specific responsible AI governance checks."""
        if metadata.get("sensitive_input_detected"):
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.AUDIT,
                GovernanceAuditStatus.FLAGGED,
            )
            self._append_flag(
                metadata,
                GovernanceFlags.SENSITIVE_INTERVIEW_CONTENT,
            )
            self._append_flag(metadata, GovernanceFlags.REQUIRES_HUMAN_REVIEW)

        if metadata.get("prompt_injection_blocked"):
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.AUDIT,
                GovernanceAuditStatus.FLAGGED,
            )
            self._append_flag(
                metadata,
                GovernanceFlags.PROMPT_INJECTION_ATTEMPT,
            )
            self._append_flag(metadata, GovernanceFlags.REQUIRES_HUMAN_REVIEW)

        if metadata.get("bias_review_required"):
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.AUDIT,
                GovernanceAuditStatus.FLAGGED,
            )
            self._append_flag(metadata, GovernanceFlags.BIAS_REVIEW_REQUIRED)
            self._append_flag(metadata, GovernanceFlags.REQUIRES_HUMAN_REVIEW)

        # Use AI-based bias detection on interview context if available
        if original_input:
            bias_check = self.bias_detector.scan(original_input, context="interview")
            if bias_check.get("risk_score", 0.0) > 0.5:
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.AUDIT,
                    GovernanceAuditStatus.FLAGGED,
                )
                self._append_flag(metadata, GovernanceFlags.BIAS_REVIEW_REQUIRED)
                self._append_flag(metadata, GovernanceFlags.REQUIRES_HUMAN_REVIEW)
                metadata["ai_bias_detection"] = bias_check

    def contains_quantifiable_claim(self, text: str | None) -> bool:
        """Return true when text contains measurable claims."""
        if not text:
            return False
        return any(
            re.search(pattern, text, flags=re.IGNORECASE)
            for pattern in settings.GOVERNANCE_QUANTIFIABLE_PATTERNS
        )

    def calculate_hallucination_risk(
        self,
        original: str | None,
        generated: str | None,
    ) -> float:
        """Calculate hallucination risk score in range [0.0, 1.0]."""
        if original is None or generated is None:
            return 1.0

        risk = 0.0

        original_words = self._extract_significant_words(original)
        generated_words = self._extract_significant_words(generated)
        new_words = generated_words - original_words

        if generated_words:
            risk = (len(new_words) / len(generated_words)) * 0.5

        if self._contains_new_numbers(original, generated):
            risk += 0.3

        if self._contains_new_proper_nouns(original, generated):
            risk += 0.2

        return min(risk, 1.0)

    def _check_hallucination(
        self,
        response: AgentResponse,
        original_input: str | None,
    ) -> bool:
        """Check hallucination risk using AI-based semantic evaluation."""
        if not original_input:
            return True

        # Use AI-based hallucination evaluation
        result = self.hallucination_evaluator.evaluate_hallucination_risk(
            source=original_input,
            generated=response.content,
        )

        # Store hallucination risk in metadata for audit
        sharp_metadata = response.sharp_metadata or {}
        sharp_metadata[GovernanceFieldNames.HALLUCINATION_RISK] = result.get(
            "hallucination_risk", 0.0
        )
        response.sharp_metadata = sharp_metadata

        # Pass if risk below threshold
        return result.get("hallucination_risk", 0.0) < settings.GOVERNANCE_HALLUCINATION_RISK_THRESHOLD

    def _check_confidence_threshold(self, response: AgentResponse) -> bool:
        score = response.confidence_score
        if score is None:
            return False
        return score >= settings.GOVERNANCE_CONFIDENCE_THRESHOLD

    def _validate_content_strength_agent(
        self,
        response: AgentResponse,
        metadata: dict[str, Any],
        original_input: str | None,  # noqa: ARG002
    ) -> None:
        try:
            content = self._parse_content_json(response.content)
            if content is None:
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.CONTENT_PARSE_ERROR,
                    True,
                )
                return

            hallucination_risk = self._get_double_or_zero(
                content,
                GovernanceFieldNames.HALLUCINATION_RISK,
            )
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.HALLUCINATION_RISK,
                hallucination_risk,
            )
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.HALLUCINATION_CHECK_PASSED,
                hallucination_risk < settings.GOVERNANCE_HALLUCINATION_RISK_THRESHOLD,
            )

            suggestions = content.get("suggestions")
            if isinstance(suggestions, list):
                unfaithful_count = sum(
                    1 for suggestion in suggestions if suggestion.get("faithful") is False
                )
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.UNFAITHFUL_SUGGESTIONS,
                    unfaithful_count,
                )
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.TOTAL_SUGGESTIONS,
                    len(suggestions),
                )
                if unfaithful_count > 0:
                    self._set_governance_field(
                        metadata,
                        GovernanceFieldNames.AUDIT,
                        GovernanceAuditStatus.FLAGGED,
                    )
                    self._append_flag(
                        metadata,
                        GovernanceFlags.UNFAITHFUL_SUGGESTIONS,
                    )
                    self._append_flag(metadata, GovernanceFlags.REQUIRES_HUMAN_REVIEW)

            achievements = content.get("achievements")
            if isinstance(achievements, list):
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.HAS_QUANTIFIED_ACHIEVEMENTS,
                    any(
                        achievement.get("quantifiable") is True
                        for achievement in achievements
                    ),
                )

            skills = content.get("skills")
            if isinstance(skills, list):
                self._set_governance_field(
                    metadata,
                    GovernanceFieldNames.HIGH_EVIDENCE_SKILLS_COUNT,
                    sum(
                        1
                        for skill in skills
                        if str(skill.get("evidenceStrength", "")).upper() == "HIGH"
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            self._set_governance_field(
                metadata,
                GovernanceFieldNames.VALIDATION_ERROR,
                str(exc),
            )

    def _parse_content_json(self, content: str | None) -> dict[str, Any] | None:
        if not content:
            return None
        try:
            match = re.search(r"\{[\s\S]*\}", content, flags=re.MULTILINE)
            if match:
                return json.loads(match.group())
            return json.loads(content)
        except Exception:
            return None

    @staticmethod
    def _get_double_or_zero(node: dict[str, Any], field: str) -> float:
        raw = node.get(field)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _extract_significant_words(text: str) -> set[str]:
        tokens = re.split(r"[^a-z0-9]+", text.lower())
        return {token for token in tokens if len(token) > 3}

    @staticmethod
    def _contains_new_numbers(original: str, generated: str) -> bool:
        original_numbers = set(re.findall(r"\d+", original))
        generated_numbers = re.findall(r"\d+", generated)
        return any(number not in original_numbers for number in generated_numbers)

    @staticmethod
    def _contains_new_proper_nouns(original: str, generated: str) -> bool:
        proper_noun_pattern = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
        original_nouns = {
            match.lower() for match in proper_noun_pattern.findall(original)
        }
        generated_nouns = proper_noun_pattern.findall(generated)
        return any(noun.lower() not in original_nouns for noun in generated_nouns)
