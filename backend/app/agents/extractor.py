"""Extractor agent for converting resume PDFs into Resume model data using LLM."""

from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.core.logging import logger
from langfuse import observe
from ..core.config import settings
from app.models import AgentResponse, Resume, ResumeDocument
from app.core.security_constants import ANTI_JAILBREAK_DIRECTIVE
from app.models.session import SessionContext
from app.utils.pdf_parser import parse_pdf_base64
from app.utils.json_parser import parse_json_object
from app.utils.validators import is_valid_url, is_full_url, is_valid_date


class ExtractorAgent(BaseAgent):
    """LLM-powered resume extraction agent with structured output."""

    USE_MOCK_RESPONSE = settings.MOCK_EXTRACTOR_AGENT
    MOCK_RESPONSE_KEY = "ExtractorAgent"
    CONFIDENCE_SCORE = 0.95

    SYSTEM_PROMPT = ("""You are an expert resume parser. Extract structured information from resume text and return it as JSON.

CRITICAL OUTPUT REQUIREMENT: You MUST respond with ONLY a valid JSON object. No text before, after, or around the JSON.

JSON RULES:
1. Your entire response must be exactly one JSON object
2. Start with '{' and end with '}' - nothing else
3. Do NOT include markdown code blocks (no ```json or ```)
4. Do NOT include explanatory text, preamble, or summary text
5. Do NOT include comments (// or /* */)
6. Every field must be present and valid
7. Use null only for optional URL fields
8. Use empty arrays [] for missing sections
9. Use empty strings "" for missing optional text fields

EXTRACTION RULES:
1. Parse the resume text carefully - ONLY extract information explicitly stated in the text
2. Extract the following JSON Resume sections: work, education, awards, certificates, skills, projects, languages, interests, references
3. CRITICAL - URL Handling:
       - Only include a url field if a URL is EXPLICITLY mentioned in the resume text
       - Do NOT infer, guess, or hallucinate URLs that are not in the source text
       - If no URL is mentioned, use null for the url field
       - Common mistakes to avoid: adding "https://github.com" when only project name is mentioned, adding company URLs when only company name is given
4. For work entries: name, position, url, startDate, endDate, summary, highlights (array)
       - url MUST be a valid URL string present in the text or null
       - Do NOT use company names or non-URL strings as url
5. For education entries: institution, url, area, studyType, startDate, endDate, score, courses (array)
       - url MUST be a valid URL present in the text or null
6. For awards: title, date, awarder, summary
7. For certificates: name, date, issuer, url
       - url MUST be a valid URL present in the text or null
8. For skills: name, level, keywords (array)
9. For projects: name, startDate, endDate, description, highlights (array), url
        - url MUST be a valid URL present in the text (e.g., "https://github.com/user/project") or null
        - If the resume only mentions "Github" without a URL, use null
10. CRITICAL - Date format: Use YYYY-MM-DD format ONLY
        - For current positions, use an empty string "" for endDate (NOT "Present", "Current", or any other text)
        - For ongoing education, use an empty string "" for endDate

Output format:
    {
        "work": [
            {
                "name": "Company Name",
                "position": "Job Title",
                "url": "https://company.com",
                "startDate": "2020-01-01",
                "endDate": "2023-01-01",
                "summary": "Role summary",
                "highlights": ["achievement1", "achievement2"]
            }
        ],
        "education": [
            {
                "institution": "University Name",
                "url": "https://institution.com",
                "area": "Software Engineering",
                "studyType": "Bachelor",
                "startDate": "2016-09-01",
                "endDate": "2020-06-01",
                "score": "3.8",
                "courses": ["DB101", "Algorithms"]
            }
        ],
        "awards": [
            {
                "title": "Award Title",
                "date": "2022-01-01",
                "awarder": "Issuer Name",
                "summary": "Award summary"
            }
        ],
        "certificates": [
            {
                "name": "Certificate Name",
                "date": "2023-01-01",
                "issuer": "Issuer Name",
                "url": "https://certificate.com"
            }
        ],
        "skills": [
            {
                "name": "Web Development",
                "level": "Advanced",
                "keywords": ["HTML", "CSS", "JavaScript"]
            }
        ],
        "projects": [
            {
                "name": "Project Title",
                "startDate": "2019-01-01",
                "endDate": "2021-01-01",
                "description": "Project description",
                "highlights": ["Won award at AIHacks 2016"],
                "url": "https://project.com"
            }
        ]
    }"""
        + ANTI_JAILBREAK_DIRECTIVE
    )

    def __init__(self, gemini_service):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ExtractorAgent",
        )

    @observe(name="extractor_process", as_type="agent")
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        session_id = getattr(context, "session_id", "unknown")
        agent_name = self.get_name()
        start_time = time.time()

        logger.debug(
            "ExtractorAgent processing started",
            session_id=session_id,
            input_length=len(input_text),
        )

        try:
            raw_result = (
                self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
                if self.USE_MOCK_RESPONSE
                else None
            )

            if self.USE_MOCK_RESPONSE and raw_result is None:
                logger.warning(
                    "Mock enabled but response key not found",
                    session_id=session_id,
                    mock_response_key=self.MOCK_RESPONSE_KEY,
                )

            payload = self._parse_payload(input_text)
            file_type = str(payload.get("fileType", "")).lower()
            if file_type != "pdf":
                raise ValueError(
                    f"Unsupported resume file type: {file_type or 'missing'}"
                )

            base64_data = payload.get("data")
            if not isinstance(base64_data, str) or not base64_data.strip():
                raise ValueError("resumeFile.data must be a non-empty base64 string")

            extracted_text = parse_pdf_base64(base64_data.strip())
            if not extracted_text:
                raise ValueError("Failed to extract text from resume PDF payload")

            resume = self._extract_resume_with_llm(
                extracted_text, extracted_text, context
            )
            resume_document = ResumeDocument(
                source="resumeFile",
                raw_text=extracted_text,
                parse_confidence=self.CONFIDENCE_SCORE,
            )
            metadata = {
                "source": "resumeFile",
                "fileType": "pdf",
                "extractedTextLength": len(extracted_text),
                "resume_document": resume_document.model_dump(exclude_none=True),
                "analysis_type": "resume_extraction",
                "confidence_score": self.CONFIDENCE_SCORE,
            }
            decision_trace = [
                "ExtractorAgent: Used LLM to parse resume PDF and extract structured data"
            ]
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.debug(
                "ExtractorAgent completed LLM-based extraction",
                session_id=session_id,
                extracted_text_length=len(extracted_text),
                processing_time_ms=elapsed_ms,
            )
            response = AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(resume.model_dump(), indent=2),
                reasoning="Extracted and structured resume data using LLM.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=decision_trace,
                sharp_metadata=metadata,
            )

            logger.debug(
                "ExtractorAgent response created",
                session_id=session_id,
                confidence_score=self.CONFIDENCE_SCORE,
                analysis_type="resume_extraction",
            )

            return response

        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.log_agent_error(agent_name, e, session_id)
            logger.error(
                "ExtractorAgent processing failed",
                session_id=session_id,
                processing_time_ms=elapsed_ms,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    @staticmethod
    def _parse_payload(input_text: str) -> dict[str, Any]:
        try:
            payload = json.loads(input_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "ExtractorAgent expected JSON payload with data and fileType"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError("ExtractorAgent payload must be a JSON object")
        return payload

    def _extract_resume_with_llm(
        self, text: str, source_text: str, source_text: str, context: SessionContext
    ) -> Resume:
        """Use LLM to extract structured resume data from text."""

        user_input = f"Extract structured information from the following resume text:\n\n{text}\n\nReturn the result as valid JSON following the specified format."

        try:
            raw_result = self.call_gemini(user_input, context)

            if not raw_result or not raw_result.strip():
                raise ValueError("Empty response received from Gemini API")

            parsed_result = parse_json_object(raw_result)

            if not parsed_result:
                raise ValueError(
                    f"Failed to parse valid JSON from Gemini response: {raw_result[:200]}..."
                )

            validated_result = Resume.model_validate(parsed_result)
            self._validate_data(validated_result, source_text)
            return validated_result

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

            return Resume()

    def _validate_data(self, resume: Resume, source_text: str) -> None:
        """Validate URLs and dates in resume data."""
        invalid_urls = []
        invalid_dates = []
        source_lower = source_text.lower()

        list_fields = ["work", "education", "certificates", "projects"]
        name_fields = {
            "work": "name",
            "education": "institution",
            "certificates": "name",
            "projects": "name",
        }

        for field in list_fields:
            items = getattr(resume, field, [])
            name_key = name_fields.get(field, "name")
            for item in items:
                item_name = getattr(item, name_key, None) or "unknown"
                self._validate_urls_for_item(
                    item, field, item_name, source_lower, invalid_urls
                )
                self._validate_dates_for_item(item, field, item_name, invalid_dates)

        errors = []
        if invalid_urls:
            errors.append(f"Invalid/hallucinated URLs: {'; '.join(invalid_urls)}")
        if invalid_dates:
            errors.append(
                f"Invalid date format (use yyyy-mm-dd, yyyy-mm, or empty): {'; '.join(invalid_dates)}"
            )

        if errors:
            raise ValueError(" ".join(errors))

    def _validate_urls_for_item(
        self,
        item: Any,
        field: str,
        item_name: str,
        source_lower: str,
        invalid_urls: list,
    ) -> None:
        url_value = getattr(item, "url", None)
        if url_value is None:
            return
        if not is_valid_url(url_value):
            invalid_urls.append(f"{field}.{item_name}: url='{url_value}' (invalid)")
        elif url_value.lower() not in source_lower and is_full_url(url_value):
            invalid_urls.append(
                f"{field}.{item_name}: url='{url_value}' (not in source)"
            )

    def _validate_dates_for_item(
        self, item: Any, field: str, item_name: str, invalid_dates: list
    ) -> None:
        for attr_name in ["startDate", "endDate", "date"]:
            attr_value = getattr(item, attr_name, None)
            if attr_value is not None and not is_valid_date(attr_value):
                invalid_dates.append(f"{field}.{item_name}: {attr_name}='{attr_value}'")
