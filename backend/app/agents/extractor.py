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
from app.models.agent import AgentInput
from app.core.constants import ANTI_JAILBREAK_DIRECTIVE
from app.models.session import SessionContext
from app.utils.pdf_parser import parse_pdf_base64
from app.utils.json_parser import parse_json_object
from app.utils.validators import is_valid_url, is_full_url, is_valid_date


class ExtractorAgent(BaseAgent):
    """LLM-powered resume extraction agent with structured output."""

    USE_MOCK_RESPONSE = settings.MOCK_EXTRACTOR_AGENT
    MOCK_RESPONSE_KEY = "ExtractorAgent"

    SYSTEM_PROMPT = (
        """You are an expert resume parser. Extract structured information from resume text and return it as JSON.

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
2. Extract the following JSON Resume sections: work, education, awards, certificates, skills, projects
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
8. For skills: name
9. For projects: name, startDate, endDate, description, highlights (array), url
        - url MUST be a valid URL present in the text (e.g., "https://github.com/user/project") or null
        - If the resume only mentions "Github" without a URL, use null
10. CRITICAL - Date format: Use YYYY-MM-DD format ONLY
        - For current positions, use an empty string "" for endDate (NOT "Present", "Current", or any other text)
        - For ongoing education, use an empty string "" for endDate

After extracting all resume data, add a "_confidence" key with this structure:
{
    "_confidence": {
        "overall": "HIGH" | "MEDIUM" | "LOW",
        "low_confidence_fields": ["work[0].startDate", "education[0].url"],
        "reasons": ["Employment dates unclear", "No institution URL in source"]
    }
}

Flag a field as low confidence if:
- The value was inferred, not explicitly stated
- The source text was ambiguous or contradictory
- You had to guess a format (especially dates)

Example low_confidence_fields format:
- "work[0].startDate" for array items
- "education[1].score" for nested array fields
- "skills[0].name" for list items

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
                "name": "Web Development"
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
    def process(
        self, input_data: AgentInput | str | bytes, context: SessionContext
    ) -> AgentResponse:
        session_id = getattr(context, "session_id", "unknown")
        start_time = time.time()

        if isinstance(input_data, AgentInput):
            raise ValueError(
                "ExtractorAgent expects a resumeFile JSON payload, not AgentInput."
            )
        if isinstance(input_data, bytes):
            input_text = input_data.decode("utf-8", errors="ignore")
        else:
            input_text = input_data

        logger.debug(
            "ExtractorAgent processing started",
            session_id=session_id,
            input_length=len(input_text),
        )

        try:
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

            if self.USE_MOCK_RESPONSE:
                resume = self._generate_mock_response(context)
                validation_errors = self._validate_data(resume, extracted_text)
                confidence_score = self._calculate_confidence_score(
                    resume=resume,
                    confidence_map={},
                    source_text=extracted_text,
                    validation_errors=validation_errors,
                )
                low_confidence_fields: list[str] = []
            else:
                resume, confidence_score, low_confidence_fields, validation_errors = (
                    self._generate_llm_response(extracted_text, context)
                )

            needs_review = confidence_score < settings.EXTRACTOR_AUTO_PROCEED_THRESHOLD

            logger.info(
                "ExtractorAgent confidence review",
                session_id=session_id,
                confidence_score=confidence_score,
                needs_review=needs_review,
                low_confidence_fields=low_confidence_fields,
            )

            resume_document = ResumeDocument(
                source="resumeFile",
                raw_text=extracted_text,
                parse_confidence=confidence_score,
            )
            metadata = {
                "source": "resumeFile",
                "fileType": "pdf",
                "extractedTextLength": len(extracted_text),
                "resume_document": resume_document.model_dump(exclude_none=True),
                "analysis_type": "resume_extraction",
                "confidence_score": confidence_score,
                "low_confidence_fields": low_confidence_fields,
                "validation_errors": validation_errors,
                "needs_review": needs_review
            }
            decision_trace = [
                "ExtractorAgent: Used LLM to parse resume PDF and extract structured data"
            ]
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.debug(
                "ExtractorAgent completed extraction",
                session_id=session_id,
                extracted_text_length=len(extracted_text),
                processing_time_ms=elapsed_ms,
                mock=self.USE_MOCK_RESPONSE,
            )

            return AgentResponse(
                agent_name=self.get_name(),
                content=json.dumps(resume.model_dump(), indent=2),
                reasoning="Extracted and structured resume data using LLM.",
                confidence_score=confidence_score,
                needs_review=needs_review,
                low_confidence_fields=low_confidence_fields,
                decision_trace=decision_trace,
                sharp_metadata=metadata,
            )

        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.log_agent_error(self.get_name(), e, session_id)
            logger.error(
                "ExtractorAgent processing failed",
                session_id=session_id,
                processing_time_ms=elapsed_ms,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _generate_mock_response(self, context: SessionContext) -> Resume:
        """Return a Resume built from the pre-configured mock response."""
        session_id = getattr(context, "session_id", "unknown")

        raw_result = self.get_mock_response_by_key(self.MOCK_RESPONSE_KEY)
        if raw_result is None:
            logger.warning(
                "Mock enabled but response key not found, returning empty Resume",
                session_id=session_id,
                mock_response_key=self.MOCK_RESPONSE_KEY,
            )
            return Resume()

        parsed_result = parse_json_object(raw_result)
        if not parsed_result:
            raise ValueError(
                f"Failed to parse valid JSON from mock response: {raw_result[:200]}..."
            )

        return Resume.model_validate(parsed_result)

    def _generate_llm_response(
        self, text: str, context: SessionContext
    ) -> tuple[Resume, float, list[str], list[str]]:
        """Use LLM to extract structured resume data from text."""
        user_input = (
            "Extract structured information from the following resume text:\n\n"
            f"{text}\n\n"
            "Return the result as valid JSON following the specified format."
        )

        raw_result = self.call_gemini(user_input, context)

        if not raw_result or not raw_result.strip():
            raise ValueError("Empty response received from Gemini API")

        parsed_result = parse_json_object(raw_result)
        if not parsed_result:
            raise ValueError(
                f"Failed to parse valid JSON from Gemini response: {raw_result[:200]}..."
            )
        if not isinstance(parsed_result, dict):
            raise ValueError("ExtractorAgent expected a JSON object response from Gemini")

        confidence_map = {}
        if isinstance(parsed_result, dict):
            confidence_map = parsed_result.pop("_confidence", {}) or {}

        validated_result = Resume.model_validate(parsed_result)
        validation_errors = self._validate_data(validated_result, text)
        self._handle_validation_errors(validation_errors, validated_result)

        confidence_score = self._calculate_confidence_score(
            resume=validated_result,
            confidence_map=confidence_map,
            source_text=text,
            validation_errors=validation_errors,
        )
        low_confidence_fields = confidence_map.get("low_confidence_fields", [])
        if not isinstance(low_confidence_fields, list):
            low_confidence_fields = []

        return validated_result, confidence_score, low_confidence_fields, validation_errors

    def _extract_resume_with_llm(self, text: str, context: SessionContext) -> Resume:
        """Backward-compatible wrapper for resume extraction."""
        resume, _, _, _ = self._generate_llm_response(text, context)
        return resume

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

    def _validate_data(self, resume: Resume, source_text: str) -> list[str]:
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

        return errors

    def _handle_validation_errors(
        self, errors: list[str], resume_data: Resume
    ) -> None:
        """Log validation errors without short-circuiting confidence scoring."""
        if errors:
            logger.warning(
                "ExtractorAgent validation errors handled",
                errors=errors,
                resume_preview=resume_data.model_dump(exclude_none=True),
            )

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
            try:
                setattr(item, "url", None)
            except Exception:
                pass
        elif url_value.lower() not in source_lower and is_full_url(url_value):
            invalid_urls.append(
                f"{field}.{item_name}: url='{url_value}' (not in source)"
            )
            try:
                setattr(item, "url", None)
            except Exception:
                pass

    def _validate_dates_for_item(
        self, item: Any, field: str, item_name: str, invalid_dates: list
    ) -> None:
        for attr_name in ["startDate", "endDate", "date"]:
            attr_value = getattr(item, attr_name, None)
            if attr_value is not None and not is_valid_date(attr_value):
                invalid_dates.append(
                    f"{field}.{item_name}: {attr_name}='{attr_value}'"
                )

    def _calculate_confidence_score(
        self,
        resume: Resume,
        confidence_map: dict,
        source_text: str,
        validation_errors: list[str],
    ) -> float:
        low_confidence_fields = confidence_map.get("low_confidence_fields", [])
        if not isinstance(low_confidence_fields, list):
            low_confidence_fields = []

        total_fields = self._count_total_fields(resume)
        low_confidence_count = len(low_confidence_fields)

        base_score = 1.0

        completeness_penalty = (
            1.0 - self._weighted_completeness_ratio(resume)
        ) * 0.4
        uncertainty_penalty = (low_confidence_count / max(total_fields, 1)) * 0.2
        quality_penalty = min(self._count_parser_warnings(source_text) * 0.1, 0.3)
        structure_penalty = min(self._count_missing_sections(resume) * 0.2, 0.2)
        validation_penalty = min(len(validation_errors) * 0.05, 0.1)

        uncertainty_weight = (
            settings.EXTRACTOR_UNCERTAINTY_WEIGHT
            if settings.EXTRACTOR_UNCERTAINTY_VALIDATION_COMPLETE
            else 0.0
        )

        final_score = max(
            0.0,
            base_score
            - completeness_penalty
            - (uncertainty_penalty * uncertainty_weight)
            - quality_penalty
            - structure_penalty
            - validation_penalty,
        )
        return round(final_score, 4)

    def _weighted_completeness_ratio(self, resume: Resume) -> float:
        section_fields = {
            "work": ["name", "position", "url", "startDate", "endDate", "highlights"],
            "education": [
                "institution",
                "url",
                "area",
                "studyType",
                "startDate",
                "endDate",
                "score",
                "courses",
            ],
            "skills": ["name"],
            "projects": ["name", "startDate", "endDate", "description", "highlights", "url"],
            "awards": ["title", "date", "awarder", "summary"],
            "certificates": ["name", "date", "issuer", "url"],
        }

        weights = settings.EXTRACTOR_FIELD_WEIGHTS
        section_weights = {
            "work": weights.get("required", 2.0),
            "education": weights.get("required", 2.0),
            "skills": weights.get("important", 1.5),
            "projects": weights.get("important", 1.5),
            "awards": weights.get("optional", 1.0),
            "certificates": weights.get("optional", 1.0),
        }

        total_weighted = 0.0
        filled_weighted = 0.0

        for section, fields in section_fields.items():
            items = getattr(resume, section, []) or []
            weight = float(section_weights.get(section, 1.0))
            expected_items = max(len(items), 1)
            total_weighted += expected_items * len(fields) * weight
            if not items:
                continue
            for item in items:
                for field_name in fields:
                    value = getattr(item, field_name, None)
                    if self._field_has_value(value):
                        filled_weighted += weight

        if total_weighted <= 0:
            return 0.0
        return min(filled_weighted / total_weighted, 1.0)

    def _count_total_fields(self, resume: Resume) -> int:
        section_fields = {
            "work": ["name", "position", "url", "startDate", "endDate", "highlights"],
            "education": [
                "institution",
                "url",
                "area",
                "studyType",
                "startDate",
                "endDate",
                "score",
                "courses",
            ],
            "skills": ["name"],
            "projects": ["name", "startDate", "endDate", "description", "highlights", "url"],
            "awards": ["title", "date", "awarder", "summary"],
            "certificates": ["name", "date", "issuer", "url"],
        }

        total = 0
        for section, fields in section_fields.items():
            items = getattr(resume, section, []) or []
            for item in items:
                for field_name in fields:
                    if self._field_has_value(getattr(item, field_name, None)):
                        total += 1
        return total

    @staticmethod
    def _field_has_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, list):
            return len(value) > 0
        return True

    @staticmethod
    def _count_parser_warnings(source_text: str) -> int:
        if not source_text:
            return 1
        warnings = 0
        if len(source_text.strip()) < 200:
            warnings += 1
        if "�" in source_text:
            warnings += 1
        if source_text.count("\n") <= 2:
            warnings += 1
        return warnings

    @staticmethod
    def _count_missing_sections(resume: Resume) -> int:
        expected_sections = [
            "work",
            "education",
            "skills",
            "projects",
            "awards",
            "certificates",
        ]
        missing = 0
        for section in expected_sections:
            items = getattr(resume, section, None)
            if not items:
                missing += 1
        return missing
