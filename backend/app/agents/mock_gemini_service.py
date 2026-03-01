"""Mock Gemini service for testing and development."""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..models.session import SessionContext
from .mock_config import MockConfig


class MockGeminiService:
    """Mock service for Gemini API interactions."""
    
    def __init__(self, model_name: str = "mock-gemini"):
        """Initialize mock Gemini service.
        
        Args:
            model_name: Mock model name
        """
        self.model_name = model_name
        self.call_count = 0
        self.custom_responses = self._load_custom_responses()
    
    def generate_response(
        self, 
        system_prompt: str, 
        user_input: str, 
        context: Optional[SessionContext] = None
    ) -> str:
        """Generate mock response based on system prompt and input.
        
        Args:
            system_prompt: System prompt for the model
            user_input: User input text
            context: Optional session context
            
        Returns:
            Mock response text
        """
        self.call_count += 1
        agent_key = self._resolve_agent_key(system_prompt)

        custom_response = self._get_custom_response(agent_key, user_input, context)
        if custom_response is not None:
            self._log_mock_call(agent_key, user_input, source="custom_file")
            return custom_response
        
        # Route to appropriate mock response based on system prompt
        if "Content Strength & Skills Reasoning Agent" in system_prompt:
            response = self._mock_content_strength_response(user_input, context)
            self._log_mock_call("ContentStrengthAgent", user_input, source="builtin")
            return response
        elif "Resume Critic" in system_prompt:
            response = self._mock_resume_critic_response(user_input, context)
            self._log_mock_call("ResumeCriticAgent", user_input, source="builtin")
            return response
        elif "Interview Coach" in system_prompt:
            response = self._mock_interview_coach_response(user_input, context)
            self._log_mock_call("InterviewCoachAgent", user_input, source="builtin")
            return response
        elif "Job Description Alignment Agent" in system_prompt:
            response = self._mock_job_alignment_response(user_input, context)
            self._log_mock_call("JobAlignmentAgent", user_input, source="builtin")
            return response
        else:
            response = self._mock_generic_response(user_input, context)
            self._log_mock_call("Generic", user_input, source="builtin")
            return response

    @staticmethod
    def _resolve_agent_key(system_prompt: str) -> str:
        """Resolve an internal agent key from a system prompt."""
        if "Content Strength & Skills Reasoning Agent" in system_prompt:
            return "ContentStrengthAgent"
        if "Resume Critic" in system_prompt:
            return "ResumeCriticAgent"
        if "Interview Coach" in system_prompt:
            return "InterviewCoachAgent"
        if "Job Description Alignment Agent" in system_prompt:
            return "JobAlignmentAgent"
        return "Generic"

    def _load_custom_responses(self) -> Dict[str, Any]:
        """Load custom responses from MOCK_RESPONSES_FILE if configured."""
        responses_file = MockConfig.get_mock_responses_file()
        if not responses_file:
            return {}

        try:
            file_path = Path(responses_file).expanduser().resolve()
            raw_text = file_path.read_text(encoding="utf-8")
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                return {}
            return parsed
        except Exception:
            return {}

    def _get_custom_response(
        self,
        agent_key: str,
        user_input: str,
        context: Optional[SessionContext],
    ) -> Optional[str]:
        """Get a response from custom mock file, if available."""
        if not self.custom_responses:
            return None

        agents_config = self.custom_responses.get("agents")
        if not isinstance(agents_config, dict):
            return None

        agent_config = agents_config.get(agent_key)
        if not isinstance(agent_config, dict):
            return self._render_response(self.custom_responses.get("fallback"))

        rules = agent_config.get("rules")
        if isinstance(rules, list):
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                when = rule.get("when", {})
                if self._rule_matches(when, user_input, context):
                    rendered = self._render_response(rule)
                    if rendered is not None:
                        return rendered

        default_config = agent_config.get("default")
        rendered_default = self._render_response(default_config)
        if rendered_default is not None:
            return rendered_default

        return self._render_response(self.custom_responses.get("fallback"))

    @staticmethod
    def _rule_matches(
        when_config: Any,
        user_input: str,
        context: Optional[SessionContext],
    ) -> bool:
        """Evaluate whether a rule in MOCK_RESPONSES_FILE applies."""
        if not isinstance(when_config, dict):
            return True

        contains_any = when_config.get("user_input_contains_any")
        if isinstance(contains_any, list):
            lowered_input = user_input.lower()
            lowered_terms = [str(term).lower() for term in contains_any if str(term).strip()]
            if lowered_terms and not any(term in lowered_input for term in lowered_terms):
                return False

        context_required = when_config.get("context_has")
        if isinstance(context_required, list):
            if context is None:
                return False
            for attr_name in context_required:
                value = getattr(context, str(attr_name), None)
                if value in (None, "", [], {}):
                    return False

        return True

    @staticmethod
    def _render_response(response_block: Any) -> Optional[str]:
        """Render a response block as text."""
        if not isinstance(response_block, dict):
            return None

        response_text = response_block.get("response_text")
        if isinstance(response_text, str):
            return response_text.strip()

        if "response_json" in response_block:
            try:
                return json.dumps(response_block["response_json"], indent=2)
            except Exception:
                return None

        return None

    @staticmethod
    def _log_mock_call(agent_name: str, user_input: str, source: str) -> None:
        """Log mock call details when LOG_MOCK_CALLS is enabled."""
        if not MockConfig.should_log_mock_calls():
            return
        preview = user_input[:80].replace("\n", " ")
        print(f"[MOCK:{source}] {agent_name} | input='{preview}'")
    
    def _mock_content_strength_response(self, user_input: str, context: Optional[SessionContext] = None) -> str:
        """Mock response for Content Strength Agent."""
        return json.dumps({
            "skills": [
                {
                    "name": "Python",
                    "category": "Technical",
                    "confidenceScore": 0.9,
                    "evidenceStrength": "HIGH",
                    "evidence": "Developed Python applications for 3+ years"
                },
                {
                    "name": "Project Management",
                    "category": "Soft",
                    "confidenceScore": 0.8,
                    "evidenceStrength": "MEDIUM",
                    "evidence": "Led cross-functional team projects"
                }
            ],
            "achievements": [
                {
                    "description": "Increased system efficiency by 25%",
                    "impact": "HIGH",
                    "quantifiable": True,
                    "confidenceScore": 0.95,
                    "originalText": "Improved system performance significantly"
                }
            ],
            "suggestions": [
                {
                    "original": "Improved system performance",
                    "suggested": "Increased system efficiency by 25% through optimization",
                    "rationale": "Added specific metric for clarity",
                    "faithful": True,
                    "confidenceScore": 0.85
                }
            ],
            "hallucinationRisk": 0.2,
            "summary": "Resume shows strong technical skills with quantifiable achievements"
        }, indent=2)
    
    def _mock_resume_critic_response(self, user_input: str, context: Optional[SessionContext] = None) -> str:
        """Mock response for Resume Critic Agent."""
        return """
Resume Critique Analysis:

## Structure Assessment
- Good overall organization with clear sections
- Contact information prominently displayed
- Professional summary effectively highlights key strengths

## ATS Compatibility
- Format is ATS-friendly with standard section headers
- Keywords are well-distributed throughout
- Avoids graphics and tables that could confuse ATS

## Impact Analysis
- Strong use of action verbs
- Good mix of technical and soft skills
- Could benefit from more quantifiable achievements

## Recommendations
1. Add more specific metrics to achievements
2. Include certifications section if applicable
3. Consider adding a projects section for technical work

Overall Score: 8/10
        """.strip()
    
    def _mock_interview_coach_response(self, user_input: str, context: Optional[SessionContext] = None) -> str:
        """Mock response for Interview Coach Agent."""
        if "question" in user_input.lower() or "answer" in user_input.lower():
            return """
Interview Coaching Feedback:

## Question Analysis
Your question shows good awareness of the role requirements.

## Suggested Answer Structure
1. **STAR Method**: Use Situation, Task, Action, Result
2. **Quantify Impact**: Include specific metrics
3. **Relevance**: Connect to job requirements

## Sample Response Framework
- Start with context (Situation)
- Describe your specific role (Task)  
- Detail actions taken (Action)
- Highlight measurable outcomes (Result)

## Delivery Tips
- Maintain eye contact
- Speak clearly and confidently
- Keep responses concise (2-3 minutes)

## Follow-up Questions to Prepare
- "What was the biggest challenge?"
- "How did you measure success?"
- "What would you do differently?"

Confidence Level: High
            """.strip()
        else:
            return """
Interview Preparation Guide:

## Common Question Types
1. Behavioral Questions (STAR method)
2. Technical Questions (show problem-solving)
3. Situational Questions (demonstrate judgment)
4. Culture Fit Questions (show alignment)

## Preparation Strategy
- Research the company thoroughly
- Prepare 5-7 key stories
- Practice with mock interviews
- Prepare thoughtful questions for them

## Day-of Interview Tips
- Arrive 10-15 minutes early
- Bring copies of your resume
- Have questions prepared
- Send thank-you note within 24 hours

Ready to practice specific questions?
            """.strip()
    
    def _mock_job_alignment_response(self, user_input: str, context: Optional[SessionContext] = None) -> str:
        """Mock response for Job Alignment Agent."""
        return json.dumps({
            "skillsMatch": ["Python", "JavaScript", "React", "Node.js", "SQL"],
            "missingSkills": ["AWS", "Docker", "Kubernetes", "GraphQL"],
            "experienceMatch": "Strong full-stack development experience with 5+ years in web applications",
            "fitScore": 75,
            "reasoning": "Good technical foundation with relevant experience, but missing cloud technologies mentioned in requirements"
        }, indent=2)
    
    def _mock_generic_response(self, user_input: str, context: Optional[SessionContext] = None) -> str:
        """Generic mock response for unknown agents."""
        return f"""
Mock Analysis Response:

I have analyzed your input: "{user_input[:100]}{'...' if len(user_input) > 100 else ''}"

## Key Findings
- Content has been processed successfully
- Analysis follows standard patterns
- Results are consistent with expectations

## Recommendations
- Consider providing more specific details
- Include quantifiable metrics when possible
- Structure content for clarity

## Summary
This is a mock response designed for testing and development purposes.

Confidence: 0.85
        """.strip()


class MockGeminiLiveService:
    """Mock service for Gemini Live API interactions."""
    
    def __init__(self):
        """Initialize mock Gemini Live service."""
        self.connected = True
        self.api_key = "mock-api-key"
        self.model_name = "mock-gemini-live"
        self.call_count = 0
    
    def connect(self, api_key: str, model_name: str = "mock-gemini-live") -> None:
        """Mock connect to Gemini Live API.
        
        Args:
            api_key: Mock API key
            model_name: Mock model name
        """
        self.api_key = api_key
        self.model_name = model_name
        self.connected = True
    
    def send_textAndWaitResponse(self, text: str, timeout_ms: int = 10000) -> Optional[str]:
        """Mock send text and wait for response.
        
        Args:
            text: Text to send
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Mock response text
        """
        self.call_count += 1
        
        if "hello" in text.lower() or "hi" in text.lower():
            return "Hello! I'm your mock interview coach. How can I help you prepare today?"
        elif "question" in text.lower():
            return "That's a great question! Let me help you structure a strong response using the STAR method."
        elif "practice" in text.lower():
            return "I'd be happy to practice with you! What type of question would you like to work on - behavioral, technical, or situational?"
        else:
            return f"I understand you're asking about: {text}. This is a mock response from Gemini Live service for testing purposes."
