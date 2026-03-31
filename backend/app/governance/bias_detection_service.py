"""AI-powered bias detection and fairness evaluation service.

This service uses semantic embeddings and LLM-based evaluation to detect
bias signals, protected attribute mentions, and fairness concerns in a more
robust way than pattern matching alone.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from langfuse import observe
except ImportError:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):  # type: ignore
        def decorator(func):  # type: ignore
            return func
        return decorator

try:
    from sentence_transformers import util, SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class BiasDetectionService:
    """AI-powered bias detection using embeddings and semantic similarity."""

    # Protected attribute categories and semantic anchors
    PROTECTED_ATTRIBUTES = {
        "gender": [
            "gender",
            "female",
            "male",
            "woman",
            "man",
            "transgender",
            "non-binary",
        ],
        "age": ["age", "young", "old", "junior", "senior", "experience level"],
        "race_ethnicity": [
            "race",
            "ethnicity",
            "national origin",
            "immigrant",
            "background",
        ],
        "religion": [
            "religion",
            "faith",
            "belief",
            "religious affiliation",
        ],
        "disability": ["disability", "disabled", "handicap", "accommodation need"],
        "family_status": [
            "family status",
            "marital status",
            "children",
            "parental status",
        ],
        "sexual_orientation": [
            "sexual orientation",
            "LGBTQ",
            "sexual preference",
        ],
    }

    # Bias signal indicators
    BIAS_SIGNALS = {
        "gendered_language": [
            "ninja developer",
            "rockstar engineer",
            "dominate market",
            "aggressive approach",
            "strong communication",
            "feminine traits",
            "masculine traits",
        ],
        "ageist_language": [
            "digital native",
            "young and energetic",
            "fresh perspective",
            "over the hill",
            "outdated skills",
            "keep up with",
        ],
        "ability_bias": [
            "able-bodied",
            "physically demanding",
            "vision required",
            "hearing required",
        ],
        "exclusionary_language": [
            "culture fit",
            "our kind of person",
            "team player",
            "self-starter",
        ],
    }

    # Fairness concerns to evaluate via semantic matching
    FAIRNESS_CONCERNS = [
        "Does the job description unnecessarily exclude candidates?",
        "Are there protected attributes mentioned that could bias decisions?",
        "Is the language gender-neutral and inclusive?",
        "Are essential vs nice-to-have qualifications clearly distinguished?",
        "Could this job description deter qualified candidates from applying?",
    ]

    def __init__(self) -> None:
        """Initialize embeddings model if available."""
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    @observe(name="bias_scan")
    def scan(
        self,
        text: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Scan text for bias signals and protected attributes.

        Args:
            text: The text to scan (job description, resume, or response)
            context: Optional context (e.g., "job_description", "resume", "coaching")

        Returns:
            Dictionary with bias detection results and risk scores.
        """
        if not text or len(text.strip()) < 10:
            return {
                "bias_scan_complete": True,
                "bias_risks": [],
                "protected_attributes_found": [],
                "risk_score": 0.0,
            }

        results = {
            "bias_scan_complete": True,
            "text_length": len(text),
            "context": context or "general",
            "protected_attributes_found": [],
            "bias_signals_detected": [],
            "risk_score": 0.0,
            "fairness_concerns": [],
            "recommendations": [],
        }

        # Use embedding-based semantic search if available
        if self.model is not None:
            results["protected_attributes_found"] = self._detect_attributes_semantic(
                text
            )
            results["bias_signals_detected"] = self._detect_bias_signals_semantic(text)
            fairness_concerns = self._evaluate_fairness_concerns_semantic(text)
            results["fairness_concerns"] = fairness_concerns
            results["risk_score"] = self._calculate_risk_score(
                results["protected_attributes_found"],
                results["bias_signals_detected"],
            )
            results["recommendations"] = self._generate_recommendations(
                results, context
            )
        else:
            # Fallback to simpler keyword detection if embeddings unavailable
            results["protected_attributes_found"] = self._detect_attributes_keyword(
                text
            )
            results["bias_signals_detected"] = self._detect_bias_signals_keyword(text)
            results["risk_score"] = self._calculate_risk_score(
                results["protected_attributes_found"],
                results["bias_signals_detected"],
            )

        return results

    def _detect_attributes_semantic(self, text: str) -> list[str]:
        """Detect protected attributes using semantic embeddings."""
        if not self.model:
            return self._detect_attributes_keyword(text)

        text_embedding = self.model.encode(text.lower(), convert_to_tensor=True)
        found_attributes: list[str] = []

        for attribute_type, anchors in self.PROTECTED_ATTRIBUTES.items():
            anchor_embeddings = self.model.encode(
                [a.lower() for a in anchors], convert_to_tensor=True
            )
            similarities = util.cos_sim(text_embedding, anchor_embeddings)

            # If any anchor has similarity > 0.5, flag this attribute type
            if (similarities > 0.5).any():
                found_attributes.append(attribute_type)

        return found_attributes

    def _detect_bias_signals_semantic(self, text: str) -> list[str]:
        """Detect bias signals using semantic embeddings."""
        if not self.model:
            return self._detect_bias_signals_keyword(text)

        text_embedding = self.model.encode(text.lower(), convert_to_tensor=True)
        detected_signals: list[str] = []

        for signal_type, examples in self.BIAS_SIGNALS.items():
            example_embeddings = self.model.encode(
                [e.lower() for e in examples], convert_to_tensor=True
            )
            similarities = util.cos_sim(text_embedding, example_embeddings)

            if (similarities > 0.6).any():
                detected_signals.append(signal_type)

        return detected_signals

    def _detect_attributes_keyword(self, text: str) -> list[str]:
        """Fallback: detect protected attributes via keyword matching."""
        found: list[str] = []
        text_lower = text.lower()

        for attribute_type, anchors in self.PROTECTED_ATTRIBUTES.items():
            if any(anchor.lower() in text_lower for anchor in anchors):
                found.append(attribute_type)

        return found

    def _detect_bias_signals_keyword(self, text: str) -> list[str]:
        """Fallback: detect bias signals via keyword matching."""
        detected: list[str] = []
        text_lower = text.lower()

        for signal_type, examples in self.BIAS_SIGNALS.items():
            if any(example.lower() in text_lower for example in examples):
                detected.append(signal_type)

        return detected

    def _evaluate_fairness_concerns_semantic(self, text: str) -> list[str]:
        """Evaluate fairness concerns for job descriptions."""
        if not self.model or not text:
            return []

        concerns: list[str] = []
        text_embedding = self.model.encode(text.lower(), convert_to_tensor=True)

        for concern in self.FAIRNESS_CONCERNS:
            concern_embedding = self.model.encode(concern.lower(), convert_to_tensor=True)
            similarity = float(util.cos_sim(text_embedding, concern_embedding)[0][0])

            # High similarity suggests this concern may apply
            if similarity > 0.6:
                concerns.append(concern)

        return concerns

    def _calculate_risk_score(
        self,
        attributes: list[str],
        bias_signals: list[str],
    ) -> float:
        """Calculate overall fairness risk score [0.0, 1.0]."""
        score = 0.0

        # Protected attribute mentions increase risk if not justified
        # (presence itself isn't bad, but needs context)
        score += len(attributes) * 0.2

        # Bias signals are concerning and directly increase risk
        score += len(bias_signals) * 0.3

        # Cap at 1.0
        return min(score, 1.0)

    def _generate_recommendations(
        self,
        results: dict[str, Any],
        context: str | None,
    ) -> list[str]:
        """Generate recommendations based on bias detection results."""
        recommendations: list[str] = []

        if results["risk_score"] > 0.7:
            recommendations.append(
                "High fairness risk detected. Consider human review before publishing."
            )

        if results["bias_signals_detected"]:
            for signal in results["bias_signals_detected"]:
                if signal == "gendered_language":
                    recommendations.append(
                        "Use gender-neutral language (e.g., 'developer' not 'rockstar engineer')."
                    )
                elif signal == "ageist_language":
                    recommendations.append(
                        "Remove age-related terms or implications about career stage."
                    )
                elif signal == "ability_bias":
                    recommendations.append(
                        "Clarify which physical abilities are essential vs. flexible."
                    )
                elif signal == "exclusionary_language":
                    recommendations.append(
                        "Replace culture-fit language with role-specific competencies."
                    )

        if context == "job_description" and len(results["protected_attributes_found"]) > 2:
            recommendations.append(
                "Job description mentions multiple protected attributes. "
                "Ensure these are genuine job requirements, not personal preferences."
            )

        return recommendations

    @observe(name="aggregate_fairness_metrics")
    def aggregate_dataset_metrics(
        self,
        text_items: list[str],
    ) -> dict[str, Any]:
        """Aggregate fairness metrics across a dataset.

        Args:
            text_items: Collection of texts to evaluate

        Returns:
            Dataset-level fairness metrics.
        """
        if not text_items:
            return {
                "items_scanned": 0,
                "items_with_protected_attributes": 0,
                "items_with_bias_signals": 0,
                "average_risk_score": 0.0,
                "high_risk_items": 0,
            }

        metrics = {
            "items_scanned": len(text_items),
            "items_with_protected_attributes": 0,
            "items_with_bias_signals": 0,
            "items_with_fairness_concerns": 0,
            "risk_scores": [],
            "high_risk_items": 0,
            "attribute_frequency": {},
            "bias_signal_frequency": {},
        }

        for text in text_items:
            scan = self.scan(text)
            metrics["risk_scores"].append(scan["risk_score"])

            if scan["protected_attributes_found"]:
                metrics["items_with_protected_attributes"] += 1
                for attr in scan["protected_attributes_found"]:
                    metrics["attribute_frequency"][attr] = (
                        metrics["attribute_frequency"].get(attr, 0) + 1
                    )

            if scan["bias_signals_detected"]:
                metrics["items_with_bias_signals"] += 1
                for signal in scan["bias_signals_detected"]:
                    metrics["bias_signal_frequency"][signal] = (
                        metrics["bias_signal_frequency"].get(signal, 0) + 1
                    )

            if scan["fairness_concerns"]:
                metrics["items_with_fairness_concerns"] += 1

            if scan["risk_score"] > 0.7:
                metrics["high_risk_items"] += 1

        # Calculate aggregate statistics
        if metrics["risk_scores"]:
            metrics["average_risk_score"] = sum(metrics["risk_scores"]) / len(
                metrics["risk_scores"]
            )
        else:
            metrics["average_risk_score"] = 0.0

        return metrics
