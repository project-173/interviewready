"""Explainability service for AI decision transparency and attribution.

This service provides mechanisms to understand why agents made certain decisions,
what factors influenced the decision, and how to communicate that to stakeholders.
"""

from __future__ import annotations

from typing import Any

try:
    from langfuse import observe
except ImportError:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):  # type: ignore
        def decorator(func):  # type: ignore
            return func
        return decorator

try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class ExplainabilityService:
    """Service for explaining AI decisions and providing transparency."""

    def __init__(self) -> None:
        """Initialize explainability components."""
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    @observe(name="decision_attribution")
    def attribute_decision(
        self,
        decision_output: str,
        input_context: dict[str, Any],
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Attribute a decision to key input factors.

        Args:
            decision_output: The decision or output made by the agent
            input_context: Dictionary of input factors (resume, job desc., etc.)
            agent_name: Name of the agent for context

        Returns:
            Attribution score and explanation of which inputs influenced the decision.
        """
        results = {
            "agent": agent_name or "unknown",
            "decision": decision_output,
            "attributions": [],
            "key_factors": [],
            "confidence": 0.0,
            "transparency_score": 0.0,
        }

        if not decision_output or not input_context:
            return results

        if self.model is None:
            # Fallback analysis
            results["attributions"] = self._analyze_keywords(decision_output, input_context)
        else:
            # Semantic-based attribution
            results["attributions"] = self._semantic_attribution(
                decision_output, input_context
            )

        # Calculate key factors (top contributors)
        if results["attributions"]:
            sorted_attrs = sorted(
                results["attributions"],
                key=lambda x: x.get("score", 0),
                reverse=True,
            )
            results["key_factors"] = sorted_attrs[:3]
            avg_score = sum(a.get("score", 0) for a in results["attributions"]) / len(
                results["attributions"]
            )
            results["confidence"] = min(avg_score, 1.0)

        # Transparency score (how explainable is this decision)
        results["transparency_score"] = self._calculate_transparency(results)

        return results

    def _semantic_attribution(
        self,
        decision: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Use semantic similarity to identify which inputs influenced the decision."""
        if not self.model:
            return self._analyze_keywords(decision, context)

        decision_embedding = self.model.encode(decision, convert_to_tensor=True)
        attributions: list[dict[str, Any]] = []

        for key, value in context.items():
            if isinstance(value, str) and len(value) > 10:
                value_embedding = self.model.encode(value, convert_to_tensor=True)
                similarity = float(util.cos_sim(decision_embedding, value_embedding)[0][0])

                if similarity > 0.2:  # Threshold for relevance
                    attributions.append(
                        {
                            "factor": key,
                            "relevance": "semantic_similarity",
                            "score": similarity,
                            "description": f"Decision correlated with {key}",
                        }
                    )

        return attributions

    def _analyze_keywords(
        self,
        decision: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fallback keyword-based attribution."""
        decision_lower = decision.lower()
        attributions: list[dict[str, Any]] = []

        for key, value in context.items():
            if isinstance(value, str):
                value_lower = value.lower()
                # Simple keyword overlap
                decision_words = set(decision_lower.split())
                context_words = set(value_lower.split())
                overlap = len(decision_words & context_words)

                if overlap > 0:
                    score = min(overlap / max(len(decision_words), 1), 1.0)
                    attributions.append(
                        {
                            "factor": key,
                            "relevance": "keyword_match",
                            "score": score,
                            "description": f"{overlap} keywords match between decision and {key}",
                        }
                    )

        return attributions

    def _calculate_transparency(self, results: dict[str, Any]) -> float:
        """Calculate how transparent/explainable the decision is."""
        transparency = 0.0

        # More attributions = more transparent
        transparency += min(len(results.get("attributions", [])) * 0.1, 0.3)

        # Higher confidence in attributions = more transparent
        transparency += results.get("confidence", 0.0) * 0.4

        # Having key factors identified = more transparent
        transparency += min(len(results.get("key_factors", [])) * 0.2, 0.3)

        return min(transparency, 1.0)

    @observe(name="generate_explanation")
    def generate_explanation(
        self,
        decision: str,
        attributions: list[dict[str, Any]],
        agent_name: str | None = None,
        audience: str = "user",
    ) -> dict[str, Any]:
        """Generate human-readable explanation of a decision.

        Args:
            decision: The decision being explained
            attributions: Attribution analysis results
            agent_name: Name of the agent
            audience: Audience type ("user", "reviewer", "auditor")

        Returns:
            Explanation text and structure.
        """
        explanation = {
            "decision": decision,
            "agent": agent_name or "AI Agent",
            "audience": audience,
            "summary": "",
            "key_factors": [],
            "reasoning": "",
            "confidence_note": "",
            "limitations": [],
        }

        if not attributions:
            explanation[
                "summary"
            ] = f"The {explanation['agent']} made this decision based on the provided inputs."
            return explanation

        # Rank attributions
        ranked = sorted(attributions, key=lambda x: x.get("score", 0), reverse=True)

        # Generate summary based on audience
        if audience == "user":
            explanation[
                "summary"
            ] = f"This recommendation is based on analyzing: {', '.join([a.get('factor', 'data') for a in ranked[:2]])}."
        elif audience == "reviewer":
            explanation["summary"] = (
                f"Decision influenced by {len(ranked)} factors. "
                f"Top contributor: {ranked[0].get('factor', 'unknown')}"
            )
        elif audience == "auditor":
            explanation["summary"] = (
                f"Full decision attribution: {len(ranked)} factors analyzed. "
                f"Average influence score: {sum(a.get('score', 0) for a in ranked) / len(ranked):.3f}"
            )

        # Key factors
        for attr in ranked[:3]:
            explanation["key_factors"].append(
                {
                    "factor": attr.get("factor"),
                    "influence": attr.get("score"),
                    "description": attr.get("description"),
                }
            )

        # Reasoning
        reasoning_parts = []
        for attr in ranked[:2]:
            reasoning_parts.append(
                f"  • {attr.get('factor')}: {attr.get('description', 'contributed to decision')}"
            )
        explanation["reasoning"] = "\n".join(reasoning_parts) if reasoning_parts else "Multiple factors considered"

        # Confidence note
        avg_confidence = (
            sum(a.get("score", 0) for a in ranked) / len(ranked)
            if ranked
            else 0.0
        )
        if avg_confidence > 0.7:
            explanation["confidence_note"] = "This explanation is based on strong evidence."
        elif avg_confidence > 0.4:
            explanation[
                "confidence_note"
            ] = "This explanation is based on moderate evidence."
        else:
            explanation[
                "confidence_note"
            ] = "This explanation has limited evidence; human review recommended."

        # Limitations
        explanation["limitations"] = [
            "This explanation reflects correlations, not causation.",
            "The AI system may have additional context or patterns not highlighted here.",
            "Human judgment should complement this explanation.",
        ]

        return explanation

    @observe(name="measure_transparency")
    def measure_overall_transparency(
        self,
        responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Measure overall transparency/explainability of a set of responses.

        Args:
            responses: List of response objects with decision information

        Returns:
            Aggregate transparency metrics.
        """
        if not responses:
            return {
                "responses_analyzed": 0,
                "average_transparency": 0.0,
                "average_confidence": 0.0,
                "high_transparency": 0,
                "low_transparency": 0,
            }

        metrics = {
            "responses_analyzed": len(responses),
            "transparency_scores": [],
            "confidence_scores": [],
            "high_transparency": 0,
            "low_transparency": 0,
        }

        for resp in responses:
            # Extract relevant scores
            transparency = resp.get("transparency_score", 0.0)
            confidence = resp.get("confidence", 0.0)

            metrics["transparency_scores"].append(transparency)
            metrics["confidence_scores"].append(confidence)

            if transparency > 0.7:
                metrics["high_transparency"] += 1
            elif transparency < 0.3:
                metrics["low_transparency"] += 1

        # Calculate averages
        if metrics["transparency_scores"]:
            metrics["average_transparency"] = (
                sum(metrics["transparency_scores"]) / len(metrics["transparency_scores"])
            )
        else:
            metrics["average_transparency"] = 0.0

        if metrics["confidence_scores"]:
            metrics["average_confidence"] = (
                sum(metrics["confidence_scores"]) / len(metrics["confidence_scores"])
            )
        else:
            metrics["average_confidence"] = 0.0

        return metrics

    def quality_checklist(
        self,
        agent_response: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an explainability quality checklist for a response.

        Used for assessing whether a response meets transparency standards.

        Args:
            agent_response: Response object to evaluate

        Returns:
            Checklist of explainability criteria and their status.
        """
        checklist = {
            "has_reasoning": bool(agent_response.get("reasoning")),
            "has_confidence_score": agent_response.get("confidence_score") is not None,
            "has_decision_trace": bool(agent_response.get("decision_trace")),
            "has_audit_metadata": bool(
                agent_response.get("sharp_metadata", {}).get("governance")
            ),
            "has_explanation": bool(agent_response.get("explanation")),
            "is_human_readable": self._check_readability(
                agent_response.get("content", "")
            ),
        }

        checklist["passing_items"] = sum(checklist.values())
        checklist["total_items"] = len(checklist)
        checklist["all_checks_pass"] = (
            checklist["passing_items"] == checklist["total_items"]
        )

        return checklist

    def _check_readability(self, text: str) -> bool:
        """Check if text is reasonably human-readable."""
        if not text or len(text) < 10:
            return False

        # Simple heuristics
        has_punctuation = any(p in text for p in ".!?,-:")
        not_mostly_numbers = sum(c.isdigit() for c in text) < len(text) * 0.5
        length_ok = 20 < len(text) < 10000

        return has_punctuation and not_mostly_numbers and length_ok
