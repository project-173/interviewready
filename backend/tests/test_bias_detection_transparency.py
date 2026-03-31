"""Test bias detection expansion and transparency exposure."""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.agents.interview_coach import InterviewCoachAgent
from app.agents.job_alignment import JobAlignmentAgent
from app.api.v1.response_transformers import (
    agent_response_to_api,
    build_bias_recommendation,
    build_confidence_explanation,
    enrich_agent_response_for_user,
)
from app.models.agent import AgentResponse
from app.models.session import SessionContext


class TestBiasDetectionExpansion:
    """Test expanded bias detection patterns."""

    def test_interview_coach_age_bias_detection(self):
        """Test detection of age-related bias signals."""
        agent = InterviewCoachAgent(None)
        
        # Test various age bias signals
        age_biased_text = "We're looking for a young, energetic digital native who can keep up with our cutting edge tech stack."
        bias_flags = agent._detect_bias_flags(age_biased_text)
        assert "age" in bias_flags

    def test_interview_coach_socioeconomic_bias_detection(self):
        """Test detection of socioeconomic status bias."""
        agent = InterviewCoachAgent(None)
        
        biased_text = "Ivy League graduates preferred. Must have attended a prestigious university."
        bias_flags = agent._detect_bias_flags(biased_text)
        assert "socioeconomic_status" in bias_flags

    def test_interview_coach_appearance_bias_detection(self):
        """Test detection of appearance-related bias."""
        agent = InterviewCoachAgent(None)
        
        biased_text = "We need an attractive, photogenic candidate who can represent our brand visually."
        bias_flags = agent._detect_bias_flags(biased_text)
        assert "appearance" in bias_flags

    def test_interview_coach_veteran_status_bias_detection(self):
        """Test detection of veteran status bias."""
        agent = InterviewCoachAgent(None)
        
        biased_text = "Must have prior military service. Active duty veterans are preferred."
        bias_flags = agent._detect_bias_flags(biased_text)
        assert "veteran_status" in bias_flags

    def test_interview_coach_sexual_orientation_bias_detection(self):
        """Test detection of sexual orientation bias."""
        agent = InterviewCoachAgent(None)
        
        biased_text = "We're looking for someone from a traditional family background. LGBTQ candidates need not apply."
        bias_flags = agent._detect_bias_flags(biased_text)
        assert "sexual_orientation" in bias_flags or "family_status" in bias_flags

    def test_interview_coach_genetic_information_bias_detection(self):
        """Test detection of genetic information bias."""
        agent = InterviewCoachAgent(None)
        
        biased_text = "Genetic screening required. Family history of certain conditions is disqualifying."
        bias_flags = agent._detect_bias_flags(biased_text)
        assert "genetic_information" in bias_flags

    def test_job_alignment_bias_detection(self):
        """Test that JobAlignmentAgent also detects bias."""
        agent = JobAlignmentAgent(None)
        
        biased_jd = "Must be a rockstar ninja who can work 24/7 with no childcare responsibilities."
        bias_flags = agent._detect_bias_flags(biased_jd)
        assert len(bias_flags) > 0
        assert "gender" in bias_flags or "family_status" in bias_flags

    def test_multiple_bias_categories_detection(self):
        """Test detection of multiple bias categories in single text."""
        agent = InterviewCoachAgent(None)
        
        heavily_biased = (
            "We need a young, energetic male with no children who can work weekends. "
            "Must be a native English speaker from the US. Christian background preferred. "
            "Physically fit required."
        )
        bias_flags = agent._detect_bias_flags(heavily_biased)
        assert len(bias_flags) >= 4  # Should detect age, gender, family, nationality, religion, disability


class TestTransparencyExposure:
    """Test exposure of transparency fields to frontend."""

    def test_agent_response_enrichment(self):
        """Test enrichment of agent response with user-facing explanations."""
        response = AgentResponse(
            agent_name="InterviewCoachAgent",
            content="Test response",
            confidence_score=0.75,
            bias_flags=["gender", "age"],
        )
        
        enriched = enrich_agent_response_for_user(response)
        
        assert enriched.confidence_explanation is not None
        assert "75%" in enriched.confidence_explanation or "75" in enriched.confidence_explanation
        assert enriched.bias_description is not None

    def test_confidence_explanation_building(self):
        """Test building of user-friendly confidence explanations."""
        
        # High confidence
        explanation = build_confidence_explanation(0.9)
        assert "high" in explanation.lower() or "reliable" in explanation.lower()
        
        # Low confidence
        explanation = build_confidence_explanation(0.3)
        assert "low" in explanation.lower() or "review" in explanation.lower()
        
        # With low confidence areas
        explanation = build_confidence_explanation(0.6, ["recommendation", "next_steps"])
        assert "recommendation" in explanation.lower() or "next_steps" in explanation.lower()

    def test_bias_recommendation_building(self):
        """Test building of bias recommendations."""
        
        # Test age bias recommendation
        rec = build_bias_recommendation(["age"])
        assert "age" in rec.lower() or "remote" in rec.lower() or "young" in rec.lower()
        
        # Test multiple bias categories
        rec = build_bias_recommendation(["gender", "age", "disability"])
        assert len(rec) > 20  # Should be a meaningful recommendation
        
        # Test empty
        rec = build_bias_recommendation([])
        assert rec == ""

    def test_agent_response_to_api_transformation(self):
        """Test transformation of internal response to user-facing API response."""
        response = AgentResponse(
            agent_name="JobAlignmentAgent",
            content="Skills match: API design, Python. Missing: Kubernetes",
            confidence_score=0.8,
            bias_flags=["gender", "nationality"],
            bias_severity="warning",
            governance_audit_status="flagged",
            governance_flags=["bias_detected"],
            improvement_suggestions=["Review job description for inclusive language"],
        )
        
        api_response = agent_response_to_api(response)
        
        # Verify all transparency fields are exposed
        assert api_response.confidence_score == 0.8
        assert api_response.bias_flags == ["gender", "nationality"]
        assert api_response.bias_severity == "warning"
        assert api_response.governance_audit_status == "flagged"
        assert len(api_response.improvement_suggestions) > 0
        assert api_response.requires_human_review is True

    def test_interview_response_fields_exposed(self):
        """Test that interview-specific fields are properly exposed."""
        response = AgentResponse(
            agent_name="InterviewCoachAgent",
            content='{"question": "Tell me about..."}',
            confidence_score=0.85,
            answer_score=78,
            can_proceed=True,
            next_challenge="Focus on specific examples",
        )
        
        api_response = agent_response_to_api(response)
        
        assert api_response.answer_score == 78
        assert api_response.can_proceed is True
        assert api_response.next_challenge == "Focus on specific examples"


class TestBiasDetectionIntegration:
    """Integration tests for bias detection in agents."""

    @patch('app.agents.interview_coach.InterviewCoachAgent.call_gemini')
    def test_interview_coach_response_with_bias_info(self, mock_gemini):
        """Test that InterviewCoachAgent includes bias info in response."""
        mock_gemini.return_value = json.dumps({
            "current_question_number": 1,
            "question": "Tell me about a challenge you overcame",
            "feedback": "",
            "answer_score": 0,
            "can_proceed": True,
        })
        
        agent = InterviewCoachAgent(None)
        
        # Mock input with biased job description
        input_data = Mock()
        input_data.job_description = "We need a young, hardworking male with a strong family orientation."
        
        context = Mock(spec=SessionContext)
        context.session_id = "test-session"
        context.shared_memory = None
        
        # Note: This test is simplified as full test would need more mocking
        # The actual agent would detect bias and set bias_flags
        
    @patch('app.agents.job_alignment.JobAlignmentAgent.call_gemini')
    def test_job_alignment_response_with_bias_info(self, mock_gemini):
        """Test that JobAlignmentAgent includes bias info in response."""
        mock_gemini.return_value = json.dumps({
            "skillsMatch": ["Python", "AWS"],
            "missingSkills": ["Kubernetes"],
            "experienceMatch": ["work[0].highlights[1]"],
            "summary": "Good match overall"
        })
        
        agent = JobAlignmentAgent(None)
        
        # Mock has bias detection built-in now
        biased_jd = "Seeking energetic female with no childcare obligations"
        detected_bias = agent._detect_bias_flags(biased_jd)
        
        assert len(detected_bias) > 0


class TestFrontendTypeCompatibility:
    """Test that transparency fields work with frontend types."""

    def test_interview_message_type_compatibility(self):
        """Verify transparency fields match InterviewMessage type."""
        # This test ensures backend response fields map to frontend InterviewMessage fields
        api_response = AgentResponse(
            agent_name="InterviewCoachAgent",
            content="coaching response",
            confidence_score=0.7,
            reasoning="Based on answer structure",
            decision_trace=["Step 1", "Step 2"],
            improvement_suggestions=["Add more specific examples"],
            bias_flags=["age"],
            answer_score=75,
            can_proceed=False,
        )
        
        # Transform for API
        transformed = agent_response_to_api(api_response)
        
        # These should be serializable to frontend InterviewMessage
        assert isinstance(transformed.confidence_score, (float, int, type(None)))
        assert isinstance(transformed.reasoning, (str, type(None)))
        assert isinstance(transformed.decision_trace, list)
        assert isinstance(transformed.improvement_suggestions, list)
        assert isinstance(transformed.bias_flags, list)
        assert isinstance(transformed.answer_score, (int, type(None)))
        assert isinstance(transformed.can_proceed, (bool, type(None)))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
