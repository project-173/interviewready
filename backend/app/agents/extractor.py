"""Extractor agent for converting resume PDFs into Resume model data using LLM."""

from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.core.logging import logger
from app.models import AgentResponse, Award, Certification, Education, Experience, Project, Resume
from app.models.session import SessionContext
from app.utils.pdf_parser import parse_pdf_base64
from app.utils.json_parser import parse_json_object

class ExtractorAgent(BaseAgent):
    """LLM-powered resume extraction agent with structured output."""

    SYSTEM_PROMPT = """You are an expert resume parser. Extract structured information from resume text and return it as JSON.

    Instructions:
    1. Parse the resume text carefully
    2. Extract the following sections: skills, experiences, educations, projects, certifications, awards
    3. Return valid JSON that matches the Resume model structure
    4. If a section is missing, return an empty array for that field
    5. For experiences: extract company, role, duration, and achievements (as array)
    6. For educations: extract institution, degree, and year
    7. For projects: extract title, description, and date (if available)
    8. For certifications: extract name, issuer, and date (if available)
    9. For awards: extract title, issuer, and date (if available)
    10. For skills: extract individual skills as strings

    Output format:
    {
        "skills": ["skill1", "skill2", ...],
        "experiences": [
            {
                "company": "Company Name",
                "role": "Job Title", 
                "duration": "2020-2023",
                "achievements": ["achievement1", "achievement2", ...]
            }
        ],
        "educations": [
            {
                "institution": "University Name",
                "degree": "Degree Name",
                "year": "2020"
            }
        ],
        "projects": [
            {
                "title": "Project Title",
                "description": "Project description",
                "date": "2022"
            }
        ],
        "certifications": [
            {
                "name": "Certification Name",
                "issuer": "Issuer Name", 
                "date": "2023"
            }
        ],
        "awards": [
            {
                "title": "Award Title",
                "issuer": "Issuer Name",
                "date": "2022"
            }
        ]
    }"""

    def __init__(self, gemini_service: object):
        super().__init__(
            gemini_service=gemini_service, system_prompt=self.SYSTEM_PROMPT, name="ExtractorAgent"
        )

    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        payload = self._parse_payload(input_text)
        file_type = str(payload.get("fileType", "")).lower()
        if file_type != "pdf":
            raise ValueError(f"Unsupported resume file type: {file_type or 'missing'}")

        base64_data = payload.get("data")
        if not isinstance(base64_data, str) or not base64_data.strip():
            raise ValueError("resumeFile.data must be a non-empty base64 string")

        extracted_text = parse_pdf_base64(base64_data.strip())
        if not extracted_text:
            raise ValueError("Failed to extract text from resume PDF payload")

        resume = self._extract_resume_with_llm(extracted_text)
        metadata = {
            "source": "resumeFile",
            "fileType": "pdf",
            "extractedTextLength": len(extracted_text),
        }
        trace = ["ExtractorAgent: Used LLM to parse resume PDF and extract structured data"]
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.debug(
            "ExtractorAgent completed LLM-based extraction",
            session_id=session_id,
            extracted_text_length=len(extracted_text),
            processing_time_ms=elapsed_ms,
        )
        return AgentResponse(
            agent_name=self.get_name(),
            content=json.dumps(resume.model_dump(), indent=2),
            reasoning="Extracted and structured resume data using LLM.",
            confidence_score=0.95,
            decision_trace=trace,
            sharp_metadata=metadata,
        )

    @staticmethod
    def _parse_payload(input_text: str) -> dict[str, Any]:
        try:
            payload = json.loads(input_text)
        except json.JSONDecodeError as exc:
            raise ValueError("ExtractorAgent expected JSON payload with data and fileType") from exc
        if not isinstance(payload, dict):
            raise ValueError("ExtractorAgent payload must be a JSON object")
        return payload

    def _extract_resume_with_llm(self, text: str) -> Resume:
        """Use LLM to extract structured resume data from text."""

        user_input = f"Extract structured information from the following resume text:\n\n{text}\n\nReturn the result as valid JSON following the specified format."

        try:
            raw_result = self.call_gemini(user_input, None)  

            if not raw_result or not raw_result.strip():
                raise ValueError("Empty response received from Gemini API")

            parsed_result = parse_json_object(raw_result)

            if not parsed_result:
                raise ValueError(f"Failed to parse valid JSON from Gemini response: {raw_result[:200]}...")

            validated_result = Resume.model_validate(parsed_result)
            return validated_result

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

            return Resume()
