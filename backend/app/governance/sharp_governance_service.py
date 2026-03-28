"""SHARP governance service ported from Java implementation."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.models.agent import AgentResponse


class SharpGovernanceService:
    """Audit and risk evaluation service for agent responses."""

    CONFIDENCE_THRESHOLD = 0.3
    HALLUCINATION_RISK_THRESHOLD = 0.7
    QUANTIFIABLE_PATTERNS = (
        r"\d+%",
        r"\$\d+",
        r"\d+\s*(years?|months?|weeks?)",
        r"\d+\s*(people|team members|employees)",
        r"\d+\s*(projects?|clients?|customers?)",
        r"increased?\s+by\s+\d+",
        r"reduced?\s+by\s+\d+",
        r"saved\s+\d+",
        r"improved\s+.*\d+",
    )

    def audit(
        self,
        response: AgentResponse,
        original_input: str | None = None,
    ) -> AgentResponse:
        """Audit response and attach governance metadata."""
        metadata: dict[str, Any] = dict(response.sharp_metadata or {})
        metadata["governance_audit"] = "passed"
        metadata["audit_timestamp"] = int(time.time() * 1000)

        hallucination_check = self._check_hallucination(response, original_input)
        metadata["hallucination_check_passed"] = hallucination_check

        confidence_check = self._check_confidence_threshold(response)
        metadata["confidence_check_passed"] = confidence_check

        if response.agent_name == "ContentStrengthAgent":
            self._validate_content_strength_agent(response, metadata, original_input)
        elif response.agent_name == "InterviewCoachAgent":
            self._validate_interview_coach_agent(metadata)

        flags: list[str] = []
        if not hallucination_check:
            flags.append("hallucination_risk")
        if not confidence_check:
            flags.append("low_confidence")

        if flags:
            metadata["governance_audit"] = "flagged"
            for flag in flags:
                self._append_flag(metadata, flag)

        response.sharp_metadata = metadata
        return response

    def _append_flag(self, metadata: dict[str, Any], flag: str) -> None:
        flags = list(metadata.get("audit_flags", []))
        if flag not in flags:
            flags.append(flag)
        metadata["audit_flags"] = flags

    def _validate_interview_coach_agent(self, metadata: dict[str, Any]) -> None:
        """Apply interview-specific responsible AI governance checks."""
        if metadata.get("sensitive_input_detected"):
            metadata["governance_audit"] = "flagged"
            self._append_flag(metadata, "sensitive_interview_content")
            self._append_flag(metadata, "requires_human_review")

        if metadata.get("prompt_injection_blocked"):
            metadata["governance_audit"] = "flagged"
            self._append_flag(metadata, "prompt_injection_attempt")
            self._append_flag(metadata, "requires_human_review")

        if metadata.get("bias_review_required"):
            metadata["governance_audit"] = "flagged"
            self._append_flag(metadata, "bias_review_required")
            self._append_flag(metadata, "requires_human_review")

    def contains_quantifiable_claim(self, text: str | None) -> bool:
        """Return true when text contains measurable claims."""
        if not text:
            return False
        return any(
            re.search(pattern, text, flags=re.IGNORECASE)
            for pattern in self.QUANTIFIABLE_PATTERNS
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
        if not original_input:
            return True

        sharp_metadata = response.sharp_metadata or {}
        if "hallucinationRisk" in sharp_metadata:
            risk = float(sharp_metadata["hallucinationRisk"])
            return risk < self.HALLUCINATION_RISK_THRESHOLD

        return True

    def _check_confidence_threshold(self, response: AgentResponse) -> bool:
        score = response.confidence_score
        if score is None:
            return False
        return score >= self.CONFIDENCE_THRESHOLD

    def _validate_content_strength_agent(
        self,
        response: AgentResponse,
        metadata: dict[str, Any],
        original_input: str | None,  # noqa: ARG002
    ) -> None:
        try:
            content = self._parse_content_json(response.content)
            if content is None:
                metadata["content_parse_error"] = True
                return

            hallucination_risk = self._get_double_or_zero(content, "hallucinationRisk")
            metadata["hallucinationRisk"] = hallucination_risk
            metadata["hallucination_check_passed"] = (
                hallucination_risk < self.HALLUCINATION_RISK_THRESHOLD
            )

            suggestions = content.get("suggestions")
            if isinstance(suggestions, list):
                unfaithful_count = sum(
                    1 for suggestion in suggestions if suggestion.get("faithful") is False
                )
                metadata["unfaithful_suggestions"] = unfaithful_count
                metadata["total_suggestions"] = len(suggestions)
                if unfaithful_count > 0:
                    metadata["governance_audit"] = "flagged"
                    metadata["audit_flags"] = [
                        "unfaithful_suggestions",
                        "requires_human_review",
                    ]

            achievements = content.get("achievements")
            if isinstance(achievements, list):
                metadata["has_quantified_achievements"] = any(
                    achievement.get("quantifiable") is True
                    for achievement in achievements
                )

            skills = content.get("skills")
            if isinstance(skills, list):
                metadata["high_evidence_skills_count"] = sum(
                    1
                    for skill in skills
                    if str(skill.get("evidenceStrength", "")).upper() == "HIGH"
                )
        except Exception as exc:  # noqa: BLE001
            metadata["validation_error"] = str(exc)

    def _parse_content_json(self, content: str | None) -> dict[str, Any] | None:
        if not content:
            return None
        try:
            match = re.search(r"\{[\s\S]*\}", content, flags=re.MULTILINE)
            if match:
                return json.loads(match.group())
            return json.loads(content)
        except Exception:  # noqa: BLE001
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
