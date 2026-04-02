"""Transparency and explainability utilities for user-facing metadata."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class BiasDetectionResult(BaseModel):
    """Bias detection findings with severity levels."""

    detected_categories: List[str] = []
    """Categories where biased language was detected (age, gender, nationality, etc.)"""
    
    severity: str = "info"
    """Severity: 'info' (informational), 'warning' (moderate concern), 'critical' (strong bias signal)"""
    
    description: str = ""
    """Human-readable description of detected bias"""
    
    recommendations: List[str] = []
    """Recommendations for removing bias or addressing concerns"""


class GovernanceFlags(BaseModel):
    """Governance and compliance flags for user transparency."""

    audit_status: str = "passed"
    """Overall audit status: 'passed', 'flagged', 'blocked'"""
    
    flags: List[str] = []
    """Specific governance flags (e.g., 'low_confidence', 'bias_detected', 'human_review_required')"""
    
    requires_human_review: bool = False
    """Whether human review is recommended"""
    
    bias_detection: Optional[BiasDetectionResult] = None
    """Detailed bias detection results"""


class UserTransparency(BaseModel):
    """User-facing transparency metadata for explainability and responsible AI."""

    confidence_score: Optional[float] = None
    """Confidence 0.0-1.0: How confident is the AI in this response?"""
    
    confidence_explanation: str = ""
    """Why the confidence is at this level"""
    
    reasoning_summary: str = ""
    """Brief explanation of how the AI arrived at this answer"""
    
    improvement_suggestions: List[str] = []
    """Actionable suggestions for the user to improve their answer/resume"""
    
    decision_trace: List[str] = []
    """Step-by-step reasoning path (for power users/auditors)"""
    
    low_confidence_areas: List[str] = []
    """Specific areas where the AI is less confident"""
    
    governance_flags: Optional[GovernanceFlags] = None
    """Governance and compliance information"""
    
    answer_score: Optional[int] = None
    """For interview context: score of the user's answer (0-100)"""
    
    can_proceed: Optional[bool] = None
    """For interview context: whether to advance to next question"""
    
    next_challenge_hint: Optional[str] = None
    """For interview context: what to focus on next"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return self.model_dump(exclude_none=True)
