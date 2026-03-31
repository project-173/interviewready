"""SHARP governance service - Lightweight keyword and pattern-based checks.

Uses simple, fast heuristics for bias and hallucination detection.
Langfuse handles post-hoc evaluation and scoring.
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
    """Lightweight audit and risk evaluation service for agent responses.

    Uses keyword and pattern-based checks with Langfuse for scoring.
    """

    # Lightweight bias keywords and patterns
    BIAS_KEYWORDS = {
        "age": [
            "young", "energetic", "fresh", "native", "digital native",
            "old", "senior", "retired", "millennial", "boomer", "gen z"
        ],
        "gender": [
            "he", "she", "him", "her", "guy", "girl", "man", "woman",
            "mother", "father", "wife", "husband"
        ],
        "race": [
            "caucasian", "asian", "african", "hispanic", "white", "black"
        ],
        "religion": [
            "christian", "muslim", "jewish", "hindu", "buddhist", "atheist"
        ],
        "disability": [
            "disabled", "wheelchair", "blind", "deaf", "mental illness"
        ],
    }

    def __init__(self) -> None:
        self._agent_validators: dict[
            str,
            Callable[[AgentResponse, dict[str, Any], str | None], None],
        ] = {
            "ContentStrengthAgent": self._validate_content_strength_agent,
            "InterviewCoachAgent": self._validate_interview_coach_agent,
        }

    def audit(
        self,
        response: AgentResponse,
        original_input: str | None = None,
    ) -> AgentResponse:
        """Audit response and attach governance metadata using lightweight checks."""
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

        # Lightweight hallucination check
        hallucination_check = self._check_hallucination(response, original_input)
        self._set_governance_field(
            metadata,
            GovernanceFieldNames.HALLUCINATION_CHECK_PASSED,
            hallucination_check,
        )

        # Lightweight bias check
        bias_result = self._check_bias(response, original_input)
        metadata["bias_check"] = bias_result

        confidence_check = self._check_confidence_threshold(response)
        self._set_governance_field(
            metadata,
            GovernanceFieldNames.CONFIDENCE_CHECK_PASSED,
            confidence_check,
        )

        validator = self._agent_validators.get(response.agent_name or "")
        if validator:
            validator(response, metadata, original_input)

        flags: list[str] = []
        if not hallucination_check:
            flags.append(GovernanceFlags.HALLUCINATION_RISK)
        if not confidence_check:
            flags.append(GovernanceFlags.LOW_CONFIDENCE)
        if bias_result.get("risk_score", 0.0) > 0.3:  # Lower threshold for lightweight
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
        """Publish governance metadata to Langfuse for scoring."""
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
        """Lightweight keyword-based bias detection."""
        if not response.content:
            return {"risk_score": 0.0, "bias_signals": []}

        content_lower = (response.content or "").lower()
        input_lower = (original_input or "").lower()

        # Find bias keywords in response
        response_biases = self._find_bias_keywords(content_lower)
        input_biases = self._find_bias_keywords(input_lower) if original_input else {}

        # Combine results
        all_biases = {}
        for category, found in response_biases.items():
            all_biases[category] = all_biases.get(category, 0) + len(found)
        for category, found in input_biases.items():
            all_biases[category] = all_biases.get(category, 0) + len(found)

        # Calculate risk: 0.1 per category found (max 0.7 for multiple)
        risk_score = min(len(all_biases) * 0.1, 0.7)

        bias_signals = []
        for category, count in all_biases.items():
            bias_signals.append(f"{category} ({count} keywords)")

        return {
            "response_bias": {"keywords": response_biases},
            "input_bias": {"keywords": input_biases},
            "risk_score": risk_score,
            "protected_attributes": list(all_biases.keys()),
            "bias_signals": bias_signals,
        }

    def _find_bias_keywords(self, text: str) -> dict[str, list[str]]:
        """Find bias keywords in text. Returns dict of category -> found keywords."""
        found = {}
        for category, keywords in self.BIAS_KEYWORDS.items():
            found_keywords = [kw for kw in keywords if kw in text]
            if found_keywords:
                found[category] = found_keywords
        return found

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
        """Lightweight hallucination check using heuristics."""
        if not original_input:
            return True

        # Use existing heuristic method
        risk = self.calculate_hallucination_risk(original_input, response.content)

        # Store hallucination risk in metadata
        sharp_metadata = response.sharp_metadata or {}
        sharp_metadata[GovernanceFieldNames.HALLUCINATION_RISK] = risk
        response.sharp_metadata = sharp_metadata

        # Pass if risk below threshold
        return risk < settings.GOVERNANCE_HALLUCINATION_RISK_THRESHOLD

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
