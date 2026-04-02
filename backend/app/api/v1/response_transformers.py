"""API transformation utilities for exposing agent data to frontend."""

from typing import Any, Dict, Optional, List
from app.models.agent import AgentResponse, ChatApiResponse


def agent_response_to_api(
    agent_response: AgentResponse,
    include_sharp_metadata: bool = False,
) -> ChatApiResponse:
    """Transform internal AgentResponse to user-facing ChatApiResponse with transparency.
    
    Args:
        agent_response: Internal agent response with full governance data
        include_sharp_metadata: Whether to include detailed SHARP metadata for advanced users
        
    Returns:
        User-facing API response with transparency fields exposed
    """
    # Extract governance flags from metadata
    metadata = agent_response.sharp_metadata or {}
    governance_flags = metadata.get("audit_flags", [])
    requires_human_review = (
        "requires_human_review" in governance_flags or
        metadata.get("bias_review_required", False) or
        metadata.get("requires_human_review", False)
    )
    
    # Build bias information
    bias_flags = agent_response.bias_flags or metadata.get("bias_flags", [])
    
    # Determine bias severity
    bias_severity = agent_response.bias_severity or "info"
    if bias_flags:
        if any(flag in ["critical", "strong"] for flag in bias_flags):
            bias_severity = "critical"
        elif len(bias_flags) > 2:
            bias_severity = "warning"
    
    # Build bias description
    bias_description = agent_response.bias_description or ""
    if bias_flags and not bias_description:
        bias_description = (
            f"Potential bias detected in {len(bias_flags)} categor{'ies' if len(bias_flags) > 1 else 'y'}: "
            f"{', '.join(bias_flags)}. Please review the job description for inclusive language."
        )
    
    # Build confidence explanation
    confidence_explanation = agent_response.confidence_explanation or ""
    if not confidence_explanation and agent_response.confidence_score is not None:
        score = agent_response.confidence_score
        if score >= 0.8:
            confidence_explanation = "High confidence: Response is well-supported by the provided information."
        elif score >= 0.5:
            confidence_explanation = "Moderate confidence: Some areas could use clarification or additional context."
        else:
            confidence_explanation = "Low confidence: Recommend careful review before using this response."
    
    # Determine overall governance audit status
    governance_audit_status = agent_response.governance_audit_status or "passed"
    if requires_human_review:
        governance_audit_status = "flagged"
    
    return ChatApiResponse(
        agent=agent_response.agent_name,
        payload=agent_response.content,
        confidence_score=agent_response.confidence_score,
        confidence_explanation=confidence_explanation,
        reasoning=agent_response.reasoning,
        improvement_suggestions=agent_response.improvement_suggestions or [],
        needs_review=agent_response.needs_review or requires_human_review,
        low_confidence_fields=agent_response.low_confidence_fields or [],
        # Bias & Governance - Now exposed for frontend
        bias_flags=bias_flags,
        bias_severity=bias_severity,
        bias_description=bias_description,
        governance_audit_status=governance_audit_status,
        governance_flags=governance_flags,
        requires_human_review=requires_human_review,
        # Interview-specific
        answer_score=agent_response.answer_score,
        can_proceed=agent_response.can_proceed,
        next_challenge=agent_response.next_challenge,
    )


def build_confidence_explanation(
    confidence_score: Optional[float],
    low_confidence_areas: Optional[List[str]] = None,
) -> str:
    """Build a user-friendly explanation of confidence levels.
    
    Args:
        confidence_score: Score from 0.0 to 1.0
        low_confidence_areas: Specific fields with low confidence
        
    Returns:
        Human-readable explanation
    """
    if confidence_score is None:
        return ""
    
    base_explanations = {
        0.0: "Very low confidence: Please review this response carefully.",
        0.2: "Low confidence: This response may contain errors or missing information.",
        0.4: "Moderate-low confidence: Some details need verification.",
        0.6: "Moderate confidence: Generally reliable with some areas needing clarification.",
        0.8: "High confidence: This response is well-supported and reliable.",
        1.0: "Very high confidence: This response is highly reliable.",
    }
    
    # Find closest threshold
    thresholds = sorted(base_explanations.keys())
    closest = min(thresholds, key=lambda x: abs(x - confidence_score))
    explanation = base_explanations[closest]
    
    # Add specific low-confidence areas if provided
    if low_confidence_areas:
        areas_text = ", ".join(low_confidence_areas)
        explanation += f" Low confidence areas: {areas_text}."
    
    return explanation


def build_bias_recommendation(bias_flags: List[str]) -> str:
    """Build actionable recommendations based on detected bias.
    
    Args:
        bias_flags: List of detected bias categories
        
    Returns:
        Actionable recommendation text
    """
    if not bias_flags:
        return ""
    
    recommendations = {
        "age": "Consider removing age-related language like 'young', 'energetic', or 'digital native'.",
        "gender": "Remove gendered pronouns and language like 'rockstar', 'ninja', or 'manpower'.",
        "nationality": "Avoid requiring 'native English' or 'local hire only' unless essential.",
        "disability": "Don't require 'able-bodied' or 'perfect health' unless job-critical.",
        "family_status": "Avoid references to family status, children, or availability assumptions.",
        "religion": "Don't mention religious requirements or accommodate only specific faiths.",
        "socioeconomic_status": "Avoid educational institution prestige requirements unless essential.",
        "sexual_orientation": "Don't infer or require sexual orientation or family structure.",
        "genetic_information": "Don't request genetic tests or family medical history.",
        "appearance": "Avoid appearance requirements, dress codes, or physical measurements.",
        "veteran_status": "Don't discriminate based on military service history.",
    }
    
    matched_recs = [recommendations[cat] for cat in bias_flags if cat in recommendations]
    if matched_recs:
        return " ".join(matched_recs)
    
    return f"Please review for inclusive language regarding: {', '.join(bias_flags)}"


def enrich_agent_response_for_user(
    agent_response: AgentResponse,
) -> AgentResponse:
    """Enrich agent response with user-facing explanations.
    
    This adds explanation fields without modifying the core response.
    
    Args:
        agent_response: Internal agent response
        
    Returns:
        Agent response with added user-facing explanations
    """
    # Build confidence explanation if not present
    if agent_response.confidence_score and not agent_response.confidence_explanation:
        agent_response.confidence_explanation = build_confidence_explanation(
            agent_response.confidence_score,
            agent_response.low_confidence_fields,
        )
    
    # Build bias recommendation if not present
    if agent_response.bias_flags and not agent_response.bias_description:
        agent_response.bias_description = build_bias_recommendation(agent_response.bias_flags)
    
    return agent_response
