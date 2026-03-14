"""Edit Plan Agent implementation."""

from __future__ import annotations

import json
from typing import Any

from .base import BaseAgent
from ..core.logging import logger
from ..models.agent import AgentResponse, ActionPlan
from ..models.session import SessionContext


class EditPlanAgent(BaseAgent):
    """Synthesizes analysis artifacts into a bounded ActionPlan."""

    SYSTEM_PROMPT = "You are a deterministic edit plan synthesizer."

    def __init__(self, gemini_service: object):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="EditPlanAgent",
        )

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        session_id = getattr(context, "session_id", "unknown")
        artifacts = (context.shared_memory or {}).get("artifacts", [])
        actions, summary, priority, counts = self._synthesize_actions(artifacts)
        no_change = len(actions) == 0

        if no_change:
            summary = "No changes recommended."
            priority = "LOW"

        governance_summary = self._summarize_governance(artifacts)
        action_plan = ActionPlan(
            summary=summary,
            actions=actions,
            priority=priority,
            no_change=no_change,
            metadata={
                "artifact_count": counts["total"],
                "action_counts": counts,
                "governance": governance_summary,
            },
        )

        logger.debug(
            "EditPlanAgent synthesized action plan",
            session_id=session_id,
            action_count=len(actions),
            priority=priority,
            no_change=no_change,
        )

        trace = list(context.decision_trace or [])
        trace.append("EditPlanAgent: Synthesized action plan from artifacts.")
        context.decision_trace = trace

        return AgentResponse(
            agent_name=self.get_name(),
            content=json.dumps(action_plan.model_dump(exclude_none=True), indent=2),
            reasoning=summary or "",
            confidence_score=self._average_confidence(artifacts),
            decision_trace=trace,
            sharp_metadata={"artifact_count": counts["total"]},
        )

    @staticmethod
    def _average_confidence(artifacts: Any) -> float:
        if not isinstance(artifacts, list):
            return 0.5
        values = []
        for artifact in artifacts:
            if isinstance(artifact, dict):
                value = artifact.get("confidence_score")
                if isinstance(value, (int, float)):
                    values.append(float(value))
        if not values:
            return 0.5
        return sum(values) / len(values)

    @staticmethod
    def _synthesize_actions(artifacts: Any) -> tuple[list[str], str, str, dict[str, int]]:
        alignment_actions: list[str] = []
        structure_actions: list[str] = []
        content_actions: list[str] = []

        if isinstance(artifacts, list):
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                agent = artifact.get("agent") or artifact.get("artifact_type")
                payload = artifact.get("payload")
                if agent == "JobAlignmentAgent" and isinstance(payload, dict):
                    missing = payload.get("missingSkills", [])
                    if isinstance(missing, list):
                        for skill in missing:
                            if isinstance(skill, str) and skill.strip():
                                alignment_actions.append(
                                    f"Address missing job skill: {skill.strip()}."
                                )
                    fit_score = payload.get("fitScore")
                    if not missing and isinstance(fit_score, (int, float)) and fit_score < 70:
                        alignment_actions.append(
                            "Improve alignment by tailoring experience to the job requirements."
                        )
                elif agent == "ResumeCriticAgent" and isinstance(payload, dict):
                    for item in payload.get("formattingRecommendations", []) or []:
                        if isinstance(item, str) and item.strip():
                            structure_actions.append(f"Structure: {item.strip()}")
                    for item in payload.get("suggestions", []) or []:
                        if isinstance(item, str) and item.strip():
                            structure_actions.append(f"Structure: {item.strip()}")
                elif agent == "ContentStrengthAgent" and isinstance(payload, dict):
                    suggestions = payload.get("suggestions", [])
                    if isinstance(suggestions, list):
                        for suggestion in suggestions:
                            if not isinstance(suggestion, dict):
                                continue
                            suggested = suggestion.get("suggested")
                            original = suggestion.get("original")
                            faithful = suggestion.get("faithful")
                            prefix = "Content: "
                            if faithful is False:
                                prefix = "Content (review): "
                            if isinstance(suggested, str) and suggested.strip():
                                if isinstance(original, str) and original.strip():
                                    content_actions.append(
                                        f"{prefix}{suggested.strip()} (from: {original.strip()})"
                                    )
                                else:
                                    content_actions.append(f"{prefix}{suggested.strip()}")

        actions: list[str] = []
        if alignment_actions:
            actions.extend(alignment_actions)
        if structure_actions:
            actions.extend(structure_actions)
        if content_actions:
            actions.extend(content_actions)

        priority = "HIGH" if alignment_actions else "MEDIUM" if actions else "LOW"
        summary = f"Generated {len(actions)} edit action(s) from analysis artifacts."
        counts = {
            "alignment": len(alignment_actions),
            "structure": len(structure_actions),
            "content": len(content_actions),
            "total": len(actions),
        }
        return actions, summary, priority, counts

    @staticmethod
    def _summarize_governance(artifacts: Any) -> dict[str, Any]:
        flagged = 0
        total = 0
        flags: list[str] = []

        if isinstance(artifacts, list):
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                total += 1
                metadata = artifact.get("metadata")
                if not isinstance(metadata, dict):
                    continue
                governance = metadata.get("governance")
                if not isinstance(governance, dict):
                    continue
                if governance.get("governance_audit") == "flagged":
                    flagged += 1
                audit_flags = governance.get("audit_flags")
                if isinstance(audit_flags, list):
                    for flag in audit_flags:
                        if isinstance(flag, str) and flag not in flags:
                            flags.append(flag)

        return {
            "flagged_count": flagged,
            "total_audits": total,
            "flags": flags,
        }
