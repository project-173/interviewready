#!/usr/bin/env python3
"""Test script to verify mock mode functionality."""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set mock mode before importing agents
os.environ["MOCK_GEMINI"] = "true"
os.environ["LOG_MOCK_CALLS"] = "true"

from app.agents.content_strength import ContentStrengthAgent
from app.agents.resume_critic import ResumeCriticAgent
from app.agents.interview_coach import InterviewCoachAgent
from app.agents.job_alignment import JobAlignmentAgent
from app.agents.mock_gemini_service import MockGeminiService
from app.models.session import SessionContext


def test_mock_service():
    """Test the mock service directly."""
    print("Testing MockGeminiService...")
    mock_service = MockGeminiService()
    
    # Test content strength response
    response = mock_service.generate_response(
        system_prompt="Content Strength & Skills Reasoning Agent",
        user_input="Test resume content",
        context=None
    )
    print("✓ Mock service generated response")
    print(f"Response length: {len(response)} characters")
    return True


def test_agents():
    """Test all agents with mock mode."""
    print("\nTesting agents with mock mode...")
    
    # Create a mock gemini service (normally this would be the real service)
    mock_service = MockGeminiService()
    
    # Test each agent
    agents = [
        ContentStrengthAgent(mock_service),
        ResumeCriticAgent(mock_service),
        InterviewCoachAgent(mock_service),
        JobAlignmentAgent(mock_service)
    ]
    
    test_input = "Sample resume text for testing"
    context = SessionContext(session_id="test-session", user_id="test-user")
    
    for agent in agents:
        try:
            print(f"\nTesting {agent.get_name()}...")
            response = agent.process(test_input, context)
            print(f"✓ {agent.get_name()} processed successfully")
            print(f"  Confidence: {response.confidence_score}")
            print(f"  Content length: {len(response.content)} characters")
            print(f"  Decision trace: {len(response.decision_trace)} steps")
        except Exception as e:
            print(f"✗ {agent.get_name()} failed: {e}")
            return False
    
    return True


def test_environment_switching():
    """Test switching between mock and real mode."""
    print("\nTesting environment switching...")
    
    # Test mock mode
    os.environ["MOCK_GEMINI"] = "true"
    from app.agents.mock_config import MockConfig
    assert MockConfig.is_mock_enabled() == True
    print("✓ Mock mode enabled")
    
    # Test real mode
    os.environ["MOCK_GEMINI"] = "false"
    # Need to reload the module to pick up the change
    import importlib
    import app.agents.mock_config
    importlib.reload(app.agents.mock_config)
    from app.agents.mock_config import MockConfig as MockConfigReloaded
    assert MockConfigReloaded.is_mock_enabled() == False
    print("✓ Real mode enabled")
    
    return True


def main():
    """Run all tests."""
    print("🧪 Testing InterviewReady Mock Mode")
    print("=" * 50)
    
    tests = [
        test_mock_service,
        test_agents,
        test_environment_switching
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Mock mode is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
