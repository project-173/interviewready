"""Test script for agent implementations."""

from dotenv import load_dotenv
from app.core.config import settings
from app.agents import (
    ResumeCriticAgent, 
    ContentStrengthAgent, 
    JobAlignmentAgent, 
    InterviewCoachAgent,
    GeminiService
)
from app.models.session import SessionContext

# Load environment variables
load_dotenv()

def test_agents():
    """Test all agent implementations."""
    
    # Check if API key is available
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set")
        print("Please set it in your .env file")
        return
    
    # Initialize Gemini service
    gemini_service = GeminiService(api_key=api_key)
    
    # Initialize agents
    agents = {
        "ResumeCriticAgent": ResumeCriticAgent(gemini_service),
        "ContentStrengthAgent": ContentStrengthAgent(gemini_service),
        "JobAlignmentAgent": JobAlignmentAgent(gemini_service),
        "InterviewCoachAgent": InterviewCoachAgent(gemini_service)
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
        job_description=sample_job_description
    )
    
    # Test each agent
    print("Testing Agent Implementations")
    print("=" * 50)
    
    for agent_name, agent in agents.items():
        print(f"\nTesting {agent_name}:")
        print("-" * 30)
        
        try:
            # Use appropriate input for each agent
            if agent_name == "JobAlignmentAgent":
                input_text = sample_resume
            else:
                input_text = sample_resume
            
            response = agent.process(input_text, context)
            
            print(f"Agent Name: {response.agent_name}")
            print(f"Confidence Score: {response.confidence_score}")
            print(f"Reasoning: {response.reasoning}")
            print(f"Decision Trace: {len(response.decision_trace or [])} items")
            print(f"SHARP Metadata: {list(response.sharp_metadata.keys()) if response.sharp_metadata else []}")
            print(f"Content Length: {len(response.content or '')} characters")
            
            # Show first 200 characters of content
            if response.content:
                content_preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
                print(f"Content Preview: {content_preview}")
            
        except Exception as e:
            print(f"Error testing {agent_name}: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Agent testing completed!")

if __name__ == "__main__":
    test_agents()
