"""Per-agent evaluation tests using LLM-as-a-judge."""

import os
import pytest
from typing import Dict, Any
from dotenv import load_dotenv

from app.agents import (
    ResumeCriticAgent, 
    ContentStrengthAgent, 
    JobAlignmentAgent, 
    InterviewCoachAgent,
    GeminiService
)
from app.agents.llm_judge import LLmasJudgeEvaluator
from app.models import AgentInput, Resume, Work
from app.models.session import SessionContext
from app.core.constants import EVAL_SCORE_THRESHOLDS
from app.core.config import settings
from langfuse import Langfuse, observe

# Load environment variables
load_dotenv()

# CI/CD toggle - set to True to skip eval tests in CI
SKIP_EVAL_TESTS = settings.SKIP_EVAL_TESTS


class TestAgentEvals:
    """Test suite for per-agent LLM-as-a-judge evaluations."""
    
    @pytest.fixture(scope="class")
    def gemini_service(self):
        """Initialize Gemini service for tests."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            pytest.skip("GEMINI_API_KEY not set")
        return GeminiService(api_key=api_key)
    
    @pytest.fixture(scope="class")
    def judge_evaluator(self, gemini_service):
        """Initialize LLM judge evaluator."""
        return LLmasJudgeEvaluator(gemini_service)
    
    @pytest.fixture(scope="class")
    def sample_resume(self):
        """Sample resume data for testing."""
        return Resume(
            work=[
                Work(
                    name="Tech Corp",
                    position="Senior Software Engineer",
                    summary="Led team of 5 developers, improved system performance by 30%",
                    highlights=["Led team of 5 developers", "Improved system performance by 30%"],
                    startDate="2020-01-01",
                    endDate="2023-12-01"
                )
            ],
            skills=[],
            education=[],
            projects=[],
            awards=[],
            certificates=[]
        )
    
    @pytest.fixture(scope="class")
    def session_context(self):
        """Sample session context."""
        return SessionContext(
            session_id="test-session-123",
            user_id="test-user",
            resume_data=None
        )
    
    @pytest.fixture(params=[
        ("ResumeCriticAgent", "critique"),
        ("ContentStrengthAgent", "content_strength"), 
        ("JobAlignmentAgent", "job_alignment"),
        ("InterviewCoachAgent", "interview_coaching")
    ])
    def agent_test_case(self, request, gemini_service, sample_resume, session_context):
        """Parametrized fixture for all agent test cases."""
        agent_name, intent = request.param
        agent_class = {
            "ResumeCriticAgent": ResumeCriticAgent,
            "ContentStrengthAgent": ContentStrengthAgent,
            "JobAlignmentAgent": JobAlignmentAgent,
            "InterviewCoachAgent": InterviewCoachAgent
        }[agent_name]
        
        agent = agent_class(gemini_service)
        
        # Create appropriate input for each agent type
        if agent_name == "ResumeCriticAgent":
            agent_input = AgentInput(
                intent="RESUME_CRITIC",
                resume_data=sample_resume.model_dump(),
                jobDescription=None
            )
        elif agent_name == "ContentStrengthAgent":
            agent_input = AgentInput(
                intent="CONTENT_STRENGTH",
                resume_data=sample_resume.model_dump(),
                jobDescription=None
            )
        elif agent_name == "JobAlignmentAgent":
            agent_input = AgentInput(
                intent="ALIGNMENT",
                resume_data=sample_resume.model_dump(),
                jobDescription="Senior Software Engineer position requiring Python, React, and cloud experience"
            )
        else:  # InterviewCoachAgent
            agent_input = AgentInput(
                intent="INTERVIEW_COACH",
                resume_data=sample_resume.model_dump(),
                jobDescription="Senior Software Engineer position"
            )
        
        return agent_name, agent, agent_input, session_context
    
    @pytest.mark.skipif(SKIP_EVAL_TESTS, reason="Eval tests disabled in CI/CD")
    def test_agent_evaluations(self, agent_test_case, judge_evaluator):
        """Test each agent with LLM-as-a-judge evaluation."""
        from langfuse import Langfuse
        
        agent_name, agent, agent_input, session_context = agent_test_case
        langfuse = Langfuse()
        
        # Create a Langfuse trace for this test
        with langfuse.start_as_current_observation(
            as_type="span",
            name=f"pytest_eval_test_{agent_name}",
            metadata={
                "test_type": "pytest_agent_evaluation",
                "agent_name": agent_name,
                "intent": agent_input.intent,
                "session_id": "pytest-session-123"
            }
        ) as trace:
        
            # Get agent response
            response = agent.process(agent_input, session_context)
            
            # Get current trace ID from Langfuse
            trace_id = langfuse.get_current_trace_id()
            
            # Evaluate with LLM judge
            input_summary = f"Intent: {agent_input.intent}, Job Description: {agent_input.jobDescription[:200] if agent_input.jobDescription else 'None'}"
            evaluation = judge_evaluator.evaluate(
                agent_name=agent_name,
                input_data=input_summary,
                output=response.content or "",
                trace_id=trace_id,  # Use the actual trace ID
                intent=agent_input.intent,
                session_id="pytest-session-123",
            )
            
            # Get thresholds for this agent
            thresholds = EVAL_SCORE_THRESHOLDS.get(agent_name, {
                "min_quality_score": 0.7,
                "min_accuracy_score": 0.7,
                "min_helpfulness_score": 0.7
            })
            
            # Assert scores meet minimum thresholds
            assert evaluation.quality_score >= thresholds["min_quality_score"], (
                f"{agent_name} quality score {evaluation.quality_score} below threshold {thresholds['min_quality_score']}. "
                f"Reasoning: {evaluation.reasoning}"
            )
            
            assert evaluation.accuracy_score >= thresholds["min_accuracy_score"], (
                f"{agent_name} accuracy score {evaluation.accuracy_score} below threshold {thresholds['min_accuracy_score']}. "
                f"Reasoning: {evaluation.reasoning}"
            )
            
            assert evaluation.helpfulness_score >= thresholds["min_helpfulness_score"], (
                f"{agent_name} helpfulness score {evaluation.helpfulness_score} below threshold {thresholds['min_helpfulness_score']}. "
                f"Reasoning: {evaluation.reasoning}"
            )
            
            # Update trace with test results
            trace.update(
                output={
                    "agent_response": response.content[:500] if response.content else "",
                    "evaluation": {
                        "quality_score": evaluation.quality_score,
                        "accuracy_score": evaluation.accuracy_score,
                        "helpfulness_score": evaluation.helpfulness_score,
                        "reasoning": evaluation.reasoning,
                        "concerns": evaluation.concerns
                    },
                    "test_passed": True,
                    "thresholds": thresholds
                }
            )
            
            # Log evaluation details for manual review
            print(f"\n=== {agent_name} Evaluation ===")
            print(f"Quality: {evaluation.quality_score:.2f} (min: {thresholds['min_quality_score']})")
            print(f"Accuracy: {evaluation.accuracy_score:.2f} (min: {thresholds['min_accuracy_score']})")
            print(f"Helpfulness: {evaluation.helpfulness_score:.2f} (min: {thresholds['min_helpfulness_score']})")
            print(f"Reasoning: {evaluation.reasoning}")
            if evaluation.concerns:
                print(f"Concerns: {evaluation.concerns}")
            print(f"Trace ID: {trace_id}")
            print("=" * 40)
    
    @pytest.mark.skipif(SKIP_EVAL_TESTS, reason="Eval tests disabled in CI/CD")
    def test_judge_evaluator_initialization(self, judge_evaluator):
        """Test that judge evaluator initializes correctly."""
        assert judge_evaluator is not None
        assert judge_evaluator.gemini_service is not None
        assert judge_evaluator.langfuse is not None


if __name__ == "__main__":
    """Run eval tests manually outside of pytest."""
    if SKIP_EVAL_TESTS:
        print("Eval tests are disabled (SKIP_EVAL_TESTS=true)")
        exit(0)
    
    print("Running agent evaluation tests...")
    
    # Initialize services
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        exit(0)
    
    gemini_service = GeminiService(api_key=api_key)
    judge_evaluator = LLmasJudgeEvaluator(gemini_service)
    langfuse = Langfuse()
    
    # Test data
    sample_resume = Resume(
        work=[
            Work(
                name="Tech Corp",
                position="Senior Software Engineer",
                summary="Led team of 5 developers, improved system performance by 30%",
                highlights=["Led team of 5 developers", "Improved system performance by 30%"],
                startDate="2020-01-01",
                endDate="2023-12-01"
            )
        ],
        skills=[],
        education=[],
        projects=[],
        awards=[],
        certificates=[]
    )
    
    session_context = SessionContext(
        session_id="test-session-123",
        user_id="test-user",
        resume_data=None
    )
    
    # Test each agent
    agents_to_test = [
        (ResumeCriticAgent, "ResumeCriticAgent", "RESUME_CRITIC", None),
        (ContentStrengthAgent, "ContentStrengthAgent", "CONTENT_STRENGTH", None),
        (JobAlignmentAgent, "JobAlignmentAgent", "ALIGNMENT", "Senior Software Engineer position requiring Python, React, and cloud experience"),
        (InterviewCoachAgent, "InterviewCoachAgent", "INTERVIEW_COACH", "Senior Software Engineer position"),
    ]
    
    passed_tests = 0
    total_tests = len(agents_to_test)
    
    for agent_class, agent_name, intent, job_desc in agents_to_test:
        try:
            # Create a Langfuse trace for this test
            with langfuse.start_as_current_observation(
                as_type="span",
                name=f"eval_test_{agent_name}",
                metadata={
                    "test_type": "agent_evaluation",
                    "agent_name": agent_name,
                    "intent": intent,
                    "session_id": "test-session-123"
                }
            ) as trace:
                
                agent = agent_class(gemini_service)
                agent_input = AgentInput(
                    intent=intent,
                    resume_data=sample_resume.model_dump(),
                    jobDescription=job_desc
                )
                
                response = agent.process(agent_input, session_context)
                
                # Get current trace ID from Langfuse
                trace_id = langfuse.get_current_trace_id()
                
                input_summary = f"Intent: {intent}, Job Description: {job_desc[:200] if job_desc else 'None'}"
                evaluation = judge_evaluator.evaluate(
                    agent_name=agent_name,
                    input_data=input_summary,
                    output=response.content or "",
                    trace_id=trace_id,  # Use the actual trace ID
                    intent=intent,
                    session_id="test-session-123",
                )
                
                thresholds = EVAL_SCORE_THRESHOLDS.get(agent_name, {
                    "min_quality_score": 0.7,
                    "min_accuracy_score": 0.7,
                    "min_helpfulness_score": 0.7
                })
                
                # Check thresholds
                passed = (
                    evaluation.quality_score >= thresholds["min_quality_score"] and
                    evaluation.accuracy_score >= thresholds["min_accuracy_score"] and
                    evaluation.helpfulness_score >= thresholds["min_helpfulness_score"]
                )
                
                if passed:
                    passed_tests += 1
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                # Update trace with results
                trace.update(
                    output={
                        "agent_response": response.content[:500] if response.content else "",
                        "evaluation": {
                            "quality_score": evaluation.quality_score,
                            "accuracy_score": evaluation.accuracy_score,
                            "helpfulness_score": evaluation.helpfulness_score,
                            "reasoning": evaluation.reasoning,
                            "concerns": evaluation.concerns
                        },
                        "test_passed": passed,
                        "thresholds": thresholds
                    }
                )
                
                print(f"\n{status} {agent_name}")
                print(f"  Quality: {evaluation.quality_score:.2f} (min: {thresholds['min_quality_score']})")
                print(f"  Accuracy: {evaluation.accuracy_score:.2f} (min: {thresholds['min_accuracy_score']})")
                print(f"  Helpfulness: {evaluation.helpfulness_score:.2f} (min: {thresholds['min_helpfulness_score']})")
                print(f"  Reasoning: {evaluation.reasoning[:100]}...")
                print(f"  Trace ID: {trace_id}")
            
        except Exception as e:
            print(f"\n❌ ERROR {agent_name}: {str(e)}")
    
    print(f"\n=== Summary ===")
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
