"""Hallucination evaluation service using semantic similarity.

This service evaluates whether a generated text contains hallucinations
(unsupported or contradictory claims) by comparing semantic meaning rather
than just surface-level pattern matching.
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
    from sentence_transformers import util, SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class HallucinationEvaluationService:
    """Semantic-based hallucination detection and faithfulness evaluation."""

    # Contradiction patterns that suggest hallucination
    CONTRADICTION_TRIGGERS = [
        ("must", "cannot"),
        ("always", "never"),
        ("all", "none"),
        ("definitely", "unlikely"),
        ("certain", "doubtful"),
        ("requires", "prohibits"),
    ]

    def __init__(self) -> None:
        """Initialize semantic embeddings model."""
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self.model = None

    @observe(name="hallucination_check")
    def evaluate_hallucination_risk(
        self,
        source: str | None,
        generated: str | None,
    ) -> dict[str, Any]:
        """Evaluate hallucination risk using semantic similarity.

        Args:
            source: Original source text (resume, job description, etc.)
            generated: Generated/predicted text (agent response)

        Returns:
            Dictionary with hallucination risk metrics [0.0, 1.0]
        """
        results = {
            "hallucination_risk": 0.0,
            "is_faithful": True,
            "faithfulness_score": 1.0,
            "potential_hallucinations": [],
            "contradictions_detected": [],
            "new_entities": [],
            "semantic_alignment": 0.0,
            "unsupported_claims": [],
        }

        if not generated or not source:
            # No source to compare against
            return results

        if self.model is not None:
            # Use semantic-based evaluation
            results.update(self._evaluate_semantic(source, generated))
        else:
            # Fallback to keyword-based detection
            results.update(self._evaluate_keyword(source, generated))

        # Determine overall faithfulness
        results["is_faithful"] = results["hallucination_risk"] < 0.5
        return results

    def _evaluate_semantic(self, source: str, generated: str) -> dict[str, Any]:
        """Evaluate using semantic similarity and embeddings."""
        if not self.model:
            return self._evaluate_keyword(source, generated)

        source_lower = source.lower()
        generated_lower = generated.lower()

        # Split into sentences for granular analysis
        source_sentences = self._split_sentences(source_lower)
        generated_sentences = self._split_sentences(generated_lower)

        results = {
            "hallucination_risk": 0.0,
            "faithfulness_score": 1.0,
            "potential_hallucinations": [],
            "contradictions_detected": [],
            "new_entities": [],
            "semantic_alignment": 0.0,
            "unsupported_claims": [],
        }

        if not generated_sentences or not source_sentences:
            return results

        # Encode all sentences
        source_embeddings = self.model.encode(source_sentences, convert_to_tensor=True)
        generated_embeddings = self.model.encode(
            generated_sentences, convert_to_tensor=True
        )

        # Calculate semantic alignment
        cosine_scores = util.cos_sim(generated_embeddings, source_embeddings)
        alignment_scores = [float(row.max()) for row in cosine_scores]

        avg_alignment = sum(alignment_scores) / len(alignment_scores)
        results["semantic_alignment"] = avg_alignment

        # Identify potentially unsupported claims
        unsupported_threshold = 0.3
        for i, score in enumerate(alignment_scores):
            if score < unsupported_threshold:
                results["unsupported_claims"].append(generated_sentences[i])
                results["hallucination_risk"] += 0.15

        # Check for contradictions
        contradictions = self._detect_contradictions(source_lower, generated_lower)
        results["contradictions_detected"] = contradictions
        results["hallucination_risk"] += len(contradictions) * 0.2

        # Cap at 1.0
        results["hallucination_risk"] = min(results["hallucination_risk"], 1.0)
        results["faithfulness_score"] = 1.0 - results["hallucination_risk"]

        return results

    def _evaluate_keyword(self, source: str, generated: str) -> dict[str, Any]:
        """Fallback: Keyword-based hallucination detection."""
        source_lower = source.lower()
        generated_lower = generated.lower()

        results = {
            "hallucination_risk": 0.0,
            "faithfulness_score": 1.0,
            "potential_hallucinations": [],
            "contradictions_detected": [],
            "new_entities": [],
            "semantic_alignment": 0.0,
            "unsupported_claims": [],
        }

        # Simple keyword overlap
        source_words = set(source_lower.split())
        generated_words = set(generated_lower.split())
        new_words = generated_words - source_words

        # High ratio of new words might indicate hallucination
        if generated_words:
            new_word_ratio = len(new_words) / len(generated_words)
            results["hallucination_risk"] += new_word_ratio * 0.3

        # Check for contradictions
        contradictions = self._detect_contradictions(source_lower, generated_lower)
        results["contradictions_detected"] = contradictions
        results["hallucination_risk"] += len(contradictions) * 0.2

        results["hallucination_risk"] = min(results["hallucination_risk"], 1.0)
        results["faithfulness_score"] = 1.0 - results["hallucination_risk"]

        return results

    def _split_sentences(self, text: str) -> list[str]:
        """Simple sentence splitting."""
        import re

        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    def _detect_contradictions(self, source: str, generated: str) -> list[str]:
        """Detect logical contradictions between source and generated text."""
        contradictions: list[str] = []

        for positive, negative in self.CONTRADICTION_TRIGGERS:
            has_positive = positive in source or positive in generated
            has_negative = negative in source or negative in generated

            # Contradiction if one text says positive and other says negative
            if (positive in generated and negative in source) or (
                positive in source and negative in generated
            ):
                contradictions.append(
                    f"Contradiction: '{positive}' vs '{negative}' in source/generated"
                )

        return contradictions

    @observe(name="faithfulness_score")
    def calculate_faithfulness_score(
        self,
        claims: list[str],
        source: str,
    ) -> dict[str, Any]:
        """Score individual claims against source material for faithfulness.

        Args:
            claims: List of claims to evaluate
            source: Source text to validate against

        Returns:
            Per-claim faithfulness scores and summary.
        """
        results = {
            "claims_evaluated": len(claims),
            "faithful_claims": 0,
            "partially_faithful": 0,
            "unsupported_claims": 0,
            "claim_scores": [],
            "average_faithfulness": 0.0,
        }

        if not claims or not source:
            return results

        if self.model is None:
            # Fallback without embeddings
            return results

        source_embedding = self.model.encode(source, convert_to_tensor=True)

        for claim in claims:
            claim_embedding = self.model.encode(claim, convert_to_tensor=True)
            similarity = float(util.cos_sim(claim_embedding, source_embedding)[0][0])

            score = {"claim": claim, "faithfulness_score": similarity}
            results["claim_scores"].append(score)

            if similarity > 0.7:
                results["faithful_claims"] += 1
            elif similarity > 0.4:
                results["partially_faithful"] += 1
            else:
                results["unsupported_claims"] += 1

        if results["claim_scores"]:
            avg = sum(s["faithfulness_score"] for s in results["claim_scores"]) / len(
                results["claim_scores"]
            )
            results["average_faithfulness"] = avg

        return results

    @observe(name="content_consistency_check")
    def check_consistency(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Check internal consistency of text (avoid self-contradictions).

        Args:
            text: Text to check for internal consistency

        Returns:
            Consistency check results.
        """
        results = {
            "is_consistent": True,
            "self_contradictions": [],
            "consistency_score": 1.0,
        }

        if not text or len(text) < 50:
            return results

        if not self.model:
            return results

        sentences = self._split_sentences(text.lower())
        if len(sentences) < 2:
            return results

        # Check each pair of sentences for contradiction
        for i, sent1 in enumerate(sentences):
            for sent2 in sentences[i + 1 :]:
                for positive, negative in self.CONTRADICTION_TRIGGERS:
                    if (positive in sent1 and negative in sent2) or (
                        positive in sent2 and negative in sent1
                    ):
                        results["self_contradictions"].append(
                            f'Contradiction: "{sent1}" vs "{sent2}"'
                        )
                        results["is_consistent"] = False

        # Calculate consistency score
        if results["self_contradictions"]:
            results["consistency_score"] = max(
                0.0, 1.0 - (len(results["self_contradictions"]) * 0.1)
            )

        return results
