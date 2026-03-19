"""Extractor agent for converting resume PDFs into Resume model data using LLM."""

from __future__ import annotations

import json
import time
from typing import Any

from langfuse import observe

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.logging import logger
from app.models import AgentResponse, Resume, ResumeDocument
from app.models.session import SessionContext
from app.utils.pdf_parser import parse_pdf_base64
from app.utils.validators import is_valid_url, is_full_url, is_valid_date


class ExtractorAgent(BaseAgent):
    """LLM-powered resume extraction agent with structured output."""

    USE_MOCK_RESPONSE = settings.MOCK_EXTRACTOR_AGENT
    MOCK_RESPONSE_KEY = "ExtractorAgent"
    CONFIDENCE_SCORE = 0.95

    SYSTEM_PROMPT = """You are an expert resume parser. Extract structured information from resume text and return it as JSON.

    Instructions:
    1. Parse the resume text carefully - ONLY extract information that is explicitly stated in the text
    2. Extract the following JSON Resume sections (basics excluded):
       work, education, awards, certificates, skills, projects
    3. Return valid JSON that matches the Resume model structure
    4. If a section is missing, return an empty array for that field
    5. CRITICAL - URL Handling:
       - Only include a url field if a URL is EXPLICITLY mentioned in the resume text
       - Do NOT infer, guess, or hallucinate URLs that are not in the source text
       - If no URL is mentioned, use null for the url field
       - Common mistakes to avoid: adding "https://github.com" when only project name is mentioned, adding company URLs when only company name is given
    6. For work entries: name, position, url, startDate, endDate, summary, highlights (array)
       - url MUST be a valid URL string present in the text or null
       - Do NOT use company names or non-URL strings as url
    7. For education entries: institution, url, area, studyType, startDate, endDate, score, courses (array)
       - url MUST be a valid URL present in the text or null
    8. For awards: title, date, awarder, summary
    9. For certificates: name, date, issuer, url
       - url MUST be a valid URL present in the text or null
    10. For skills: name, level, keywords (array)
    11. For projects: name, startDate, endDate, description, highlights (array), url
        - url MUST be a valid URL present in the text (e.g., "https://github.com/user/project") or null
        - If the resume only mentions "Github" without a URL, use null
    12. CRITICAL - Date format: Use YYYY-MM-DD format ONLY
        - For current positions, use an empty string "" for endDate (NOT "Present", "Current", or any other text)
        - For ongoing education, use an empty string "" for endDate

    Return ONLY valid JSON matching the Resume model structure."""

    def __init__(self, gemini_service: object):
        super().__init__(
            gemini_service=gemini_service,
            system_prompt=self.SYSTEM_PROMPT,
            name="ExtractorAgent",
        )

    @observe
    def process(self, input_text: str, context: SessionContext) -> AgentResponse:
        """Process a base64-encoded resume PDF and return structured resume data."""
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        logger.debug(
            "ExtractorAgent processing started",
            session_id=session_id,
            input_length=len(input_text),
            input_preview=input_text[:100],
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

            extracted_text = self._extract_text_from_payload(input_text)

            user_prompt = (
                f"Extract structured information from the following resume text:\n\n"
                f"{extracted_text}\n\n"
                f"Return the result as valid JSON following the specified format."
            )
            raw_result = raw_result or self.call_gemini(user_prompt, context)

            resume = self.parse_and_validate(raw_result, Resume)
            self._validate_data(resume, extracted_text)

            resume_document = ResumeDocument(
                source="resumeFile",
                raw_text=extracted_text,
                parse_confidence=self.CONFIDENCE_SCORE,
            )

            logger.debug(
                "ExtractorAgent processing completed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
            )

            return AgentResponse(
                agent_name=self.get_name(),
                content=resume.model_dump(),
                reasoning="Extracted and structured resume data using LLM.",
                confidence_score=self.CONFIDENCE_SCORE,
                decision_trace=[
                    "ExtractorAgent: Used LLM to parse resume PDF and extract structured data",
                    f"ExtractorAgent: Extraction completed with confidence {self.CONFIDENCE_SCORE}",
                ],
                sharp_metadata={
                    "source": "resumeFile",
                    "fileType": "pdf",
                    "extractedTextLength": len(extracted_text),
                    "resume_document": resume_document.model_dump(exclude_none=True),
                },
            )

        except Exception as e:
            logger.log_agent_error(self.get_name(), e, session_id)
            logger.error(
                "ExtractorAgent processing failed",
                session_id=session_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _extract_text_from_payload(self, input_text: str) -> str:
        """Parse the JSON payload and extract text from the PDF."""
        try:
            payload = json.loads(input_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "ExtractorAgent expected JSON payload with data and fileType"
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError("ExtractorAgent payload must be a JSON object")

        file_type = str(payload.get("fileType", "")).lower()
        if file_type != "pdf":
            raise ValueError(f"Unsupported resume file type: {file_type or 'missing'}")

        base64_data = payload.get("data")
        if not isinstance(base64_data, str) or not base64_data.strip():
            raise ValueError("resumeFile.data must be a non-empty base64 string")

        extracted_text = parse_pdf_base64(base64_data.strip())
        if not extracted_text:
            raise ValueError("Failed to extract text from resume PDF payload")

        return extracted_text

    def _validate_data(self, resume: Resume, source_text: str) -> None:
        """Validate URLs and dates in extracted resume data."""
        invalid_urls: list[str] = []
        invalid_dates: list[str] = []
        source_lower = source_text.lower()

        field_name_keys = {
            "work": "name",
            "education": "institution",
            "certificates": "name",
            "projects": "name",
        }

        for field, name_key in field_name_keys.items():
            for item in getattr(resume, field, []):
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
        invalid_urls: list[str],
    ) -> None:
        url_value = getattr(item, "url", None)
        if url_value is None:
            return
        if not is_valid_url(url_value):
            invalid_urls.append(f"{field}.{item_name}: url='{url_value}' (invalid)")
        elif is_full_url(url_value) and url_value.lower() not in source_lower:
            invalid_urls.append(
                f"{field}.{item_name}: url='{url_value}' (not in source)"
            )

    def _validate_dates_for_item(
        self, item: Any, field: str, item_name: str, invalid_dates: list[str]
    ) -> None:
        for attr_name in ["startDate", "endDate", "date"]:
            attr_value = getattr(item, attr_name, None)
            if attr_value is not None and not is_valid_date(attr_value):
                invalid_dates.append(f"{field}.{item_name}: {attr_name}='{attr_value}'")
