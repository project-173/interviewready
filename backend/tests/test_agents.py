"""Test script for agent implementations."""

from dotenv import load_dotenv

from app.agents import (
    ContentStrengthAgent,
    GeminiService,
    InterviewCoachAgent,
    JobAlignmentAgent,
    ResumeCriticAgent,
)
from app.core.config import settings
from app.models import AgentInput, Resume, Work
from app.models.session import SessionContext

# Load environment variables
load_dotenv()


def test_agents():
    """Test all agent implementations."""

    # Check if API key is available
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return

    # Initialize Gemini service
    gemini_service = GeminiService(api_key=api_key)

    # Initialize agents
    agents = {
        "ResumeCriticAgent": ResumeCriticAgent(gemini_service),
        "ContentStrengthAgent": ContentStrengthAgent(gemini_service),
        "JobAlignmentAgent": JobAlignmentAgent(gemini_service),
        "InterviewCoachAgent": InterviewCoachAgent(gemini_service),
    }

    # Test data
    sample_resume = """
    John Doe
    Software Engineer

    Experience:
    - Senior Software Engineer at Tech Corp (2020-Present)
      * Led team of 5 developers
      * Improved system performance by 30%
      * Implemented microservices architecture

    - Software Developer at StartupXYZ (2018-2020)
      * Developed REST APIs using Python and Django
      * Worked on various projects to improve processes

    Skills:
    - Python, Java, JavaScript
    - AWS, Docker, Kubernetes
    - Agile, Scrum
    """

    sample_job_description = """
    Senior Software Engineer Position

    Requirements:
    - 5+ years of software development experience
    - Strong experience with Python and cloud technologies
    - Experience leading development teams
    - Knowledge of microservices architecture
    - Excellent problem-solving skills
    """

    # Create session context
    context = SessionContext(
        session_id="test_session",
        user_id="test_user",
        resume_data=sample_resume,
        job_description=sample_job_description,
    )

    resume = Resume(
        work=[
            Work(
                name="Tech Corp",
                position="Senior Software Engineer",
                highlights=[
                    "Led team of 5 developers",
                    "Improved system performance by 30%",
                    "Implemented microservices architecture",
                ],
            )
        ]
    )

    intent_map = {
        "ResumeCriticAgent": "RESUME_CRITIC",
        "ContentStrengthAgent": "CONTENT_STRENGTH",
        "JobAlignmentAgent": "ALIGNMENT",
        "InterviewCoachAgent": "INTERVIEW_COACH",
    }

    # Test each agent

    for agent_name, agent in agents.items():
        try:
            agent_input = AgentInput(
                intent=intent_map[agent_name],
                resume=resume,
                job_description=sample_job_description,
                message_history=[],
            )

            response = agent.process(agent_input, context)

            # Show first 200 characters of content
            if response.content:
                response.content[:200] + "..." if len(
                    response.content
                ) > 200 else response.content

        except Exception:
            pass


if __name__ == "__main__":
    test_agents()
