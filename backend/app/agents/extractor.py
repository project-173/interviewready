"""Extractor agent for converting resume PDFs into Resume model data."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.base import BaseAgent
from app.core.logging import logger
from app.models import AgentResponse, Award, Certification, Contact, Education, Experience, Project, Resume
from app.models.session import SessionContext
from app.utils.pdf_parser import parse_pdf_base64


class ExtractorAgent(BaseAgent):
    """Deterministically extract text from PDF payloads."""

    SYSTEM_PROMPT = "Deterministic PDF extraction agent. No LLM output required."
    SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
        "summary": re.compile(r"^(professional\s+summary|summary|profile)$", re.IGNORECASE),
        "experience": re.compile(r"^(work\s+experience|experience|employment)$", re.IGNORECASE),
        "education": re.compile(r"^education$", re.IGNORECASE),
        "projects": re.compile(r"^(projects|project)$", re.IGNORECASE),
        "certifications": re.compile(r"^(certifications|licenses?|certificates?)$", re.IGNORECASE),
        "awards": re.compile(r"^(awards?|honors?)$", re.IGNORECASE),
        "skills": re.compile(r"^skills?$", re.IGNORECASE),
    }

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

        resume = self._extract_resume(extracted_text)
        metadata = {
            "source": "resumeFile",
            "fileType": "pdf",
            "extractedTextLength": len(extracted_text),
        }
        trace = ["ExtractorAgent: Parsed resumeFile PDF and built Resume payload"]
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.debug(
            "ExtractorAgent completed PDF extraction",
            session_id=session_id,
            extracted_text_length=len(extracted_text),
            processing_time_ms=elapsed_ms,
        )
        return AgentResponse(
            agent_name=self.get_name(),
            content=json.dumps(resume.model_dump(), indent=2),
            reasoning="Extracted resume text from PDF input.",
            confidence_score=1.0,
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

    def _extract_resume(self, text: str) -> Resume:
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return Resume(summary="")

        name = lines[0]
        sections, preface = self._split_sections(lines)
        contact = self._extract_contact(lines[: min(12, len(lines))])
        location = self._extract_location(lines[: min(12, len(lines))])
        summary = self._extract_summary(preface, sections.get("summary", []))
        experience = self._extract_experiences(sections.get("experience", []))
        education = self._extract_educations(sections.get("education", []))

        return Resume(
            name=name,
            title=name,
            summary=summary,
            email=contact.email if contact else None,
            phone=contact.phone if contact else None,
            location=location,
            timestamp=datetime.now(timezone.utc).isoformat(),
            contact=contact,
            skills=self._extract_skills(sections.get("skills", [])),
            experience=experience,
            education=education,
            projects=self._extract_projects(sections.get("projects", [])),
            certifications=self._extract_certifications(sections.get("certifications", [])),
            awards=self._extract_awards(sections.get("awards", [])),
            experiences=experience,
            educations=education,
        )

    def _split_sections(self, lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
        sections: dict[str, list[str]] = {key: [] for key in self.SECTION_PATTERNS}
        preface: list[str] = []
        current: str | None = None
        for line in lines:
            matched_section = self._match_section(line)
            if matched_section:
                current = matched_section
                continue
            if current is None:
                preface.append(line)
            else:
                sections[current].append(line)
        return sections, preface

    def _match_section(self, line: str) -> str | None:
        normalized = re.sub(r"\s+", " ", line).strip().strip(":")
        for section, pattern in self.SECTION_PATTERNS.items():
            if pattern.match(normalized):
                return section
        return None

    @staticmethod
    def _extract_contact(lines: list[str]) -> Contact | None:
        text = "\n".join(lines)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(\+?\d[\d\-\s()]{7,}\d)", text)
        linkedin_match = re.search(r"(linkedin\.com/\S+)", text, re.IGNORECASE)
        github_match = re.search(r"(github\.com/\S+)", text, re.IGNORECASE)
        if not any((email_match, phone_match, linkedin_match, github_match)):
            return None
        return Contact(
            fullName=lines[0] if lines else None,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(1) if phone_match else None,
            linkedin=linkedin_match.group(1) if linkedin_match else None,
            github=github_match.group(1) if github_match else None,
        )

    @staticmethod
    def _extract_location(lines: list[str]) -> str | None:
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            lowered = line.lower()
            if "@" in line or "linkedin.com/" in lowered or "github.com/" in lowered:
                continue
            if re.search(r"\d{3,}", line):
                continue
            if "," in line and len(line) <= 80:
                return line
        return None

    @staticmethod
    def _extract_summary(preface: list[str], section_summary: list[str]) -> str | None:
        if section_summary:
            return " ".join(section_summary[:6]).strip() or None
        if len(preface) > 1:
            return " ".join(preface[1:6]).strip() or None
        if preface:
            return preface[0]
        return None

    @staticmethod
    def _tokenize_items(lines: list[str]) -> list[str]:
        joined = " ".join(lines)
        joined = joined.replace("\u2022", ",").replace("•", ",")
        parts = re.split(r",|;|\||\s{2,}", joined)
        items: list[str] = []
        for part in parts:
            value = part.strip(" -:\t")
            if value:
                items.append(value)
        return items

    def _extract_skills(self, lines: list[str]) -> list[str]:
        if not lines:
            return []
        items = self._tokenize_items(lines)
        filtered = []
        seen: set[str] = set()
        for item in items:
            if len(item) < 2:
                continue
            if re.search(r"\b(development|support|management|architecture)\b", item, re.IGNORECASE):
                continue
            key = item.lower()
            if key not in seen:
                seen.add(key)
                filtered.append(item)
        return filtered

    @staticmethod
    def _extract_experiences(lines: list[str]) -> list[Experience]:
        if not lines:
            return []
        experiences: list[Experience] = []
        current_role: str | None = None
        current_company: str | None = None
        current_duration: str | None = None
        achievement_lines: list[str] = []
        for line in lines:
            if line.startswith(("\u2022", "•", "-")):
                ExtractorAgent._append_achievement_line(
                    achievement_lines, line.lstrip("\u2022•- ").strip()
                )
                continue
            if "  " in line or " - " in line or "|" in line:
                if current_role or current_company or current_duration or achievement_lines:
                    experiences.append(
                        Experience(
                            company=current_company,
                            role=current_role,
                            duration=current_duration,
                            achievements=[item for item in achievement_lines if item],
                        )
                    )
                    achievement_lines = []
                if "  " in line:
                    parts = [p.strip() for p in line.split("  ") if p.strip()]
                    current_company = parts[0] if parts else None
                else:
                    parts = [p.strip() for p in re.split(r"\s-\s|\|", line) if p.strip()]
                    current_company = parts[0] if parts else line
                    if len(parts) > 1 and re.search(r"\d{4}", parts[-1]):
                        current_duration = parts[-1]
                current_role = None
                continue
            if not current_role:
                current_role = line
                date_match = re.search(
                    r"((?:19|20)\d{2}\s*[-\u2013]\s*(?:Present|Current|(?:19|20)\d{2}))",
                    line,
                    re.IGNORECASE,
                )
                if date_match:
                    current_duration = date_match.group(1)
                    current_role = line.replace(date_match.group(1), "").strip(" -|")
            else:
                ExtractorAgent._append_achievement_line(achievement_lines, line)
        if current_role or current_company or current_duration or achievement_lines:
            experiences.append(
                Experience(
                    company=current_company,
                    role=current_role,
                    duration=current_duration,
                    achievements=[item for item in achievement_lines if item],
                )
            )
        return experiences

    @staticmethod
    def _append_achievement_line(achievements: list[str], raw_line: str) -> None:
        """Append achievements while merging wrapped-line fragments."""
        text = raw_line.strip()
        if not text:
            return

        if achievements:
            previous = achievements[-1].rstrip()
            if text[0].islower() or previous.endswith("-"):
                if previous.endswith("-"):
                    achievements[-1] = f"{previous[:-1].rstrip()}-{text}".strip()
                else:
                    achievements[-1] = f"{previous} {text}".strip()
                return

        achievements.append(text)

    @staticmethod
    def _extract_educations(lines: list[str]) -> list[Education]:
        if not lines:
            return []
        entries = [line for line in lines if not line.startswith(("\u2022", "•", "-")) and "gpa" not in line.lower()]
        if not entries:
            return []
        year_match = re.search(r"(19|20)\d{2}", " ".join(lines))
        return [
            Education(
                institution=entries[0] if entries else None,
                degree=entries[1] if len(entries) > 1 else None,
                year=year_match.group(0) if year_match else None,
            )
        ]

    @staticmethod
    def _extract_projects(lines: list[str]) -> list[Project]:
        if not lines:
            return []
        projects: list[Project] = []
        current_title: str | None = None
        description_lines: list[str] = []
        for line in lines:
            if line.startswith(("\u2022", "•", "-")):
                description_lines.append(line.lstrip("\u2022•- ").strip())
                continue
            if current_title is not None:
                projects.append(
                    Project(
                        title=current_title,
                        description=" ".join(description_lines).strip() or None,
                        date=None,
                    )
                )
                description_lines = []
            current_title = line
        if current_title is not None:
            projects.append(
                Project(
                    title=current_title,
                    description=" ".join(description_lines).strip() or None,
                    date=None,
                )
            )
        return projects

    @staticmethod
    def _extract_certifications(lines: list[str]) -> list[Certification]:
        entries = [line.lstrip("\u2022•- ").strip() for line in lines if line.strip()]
        certifications: list[Certification] = []
        for entry in entries:
            parts = [p.strip() for p in re.split(r"\s-\s|\|", entry) if p.strip()]
            name = parts[0] if parts else entry
            issuer = parts[1] if len(parts) > 1 else None
            date = parts[2] if len(parts) > 2 else None
            certifications.append(Certification(name=name, issuer=issuer, date=date))
        return certifications

    @staticmethod
    def _extract_awards(lines: list[str]) -> list[Award]:
        entries = [line.lstrip("\u2022•- ").strip() for line in lines if line.strip()]
        awards: list[Award] = []
        for entry in entries:
            parts = [p.strip() for p in re.split(r"\s-\s|\|", entry) if p.strip()]
            title = parts[0] if parts else entry
            issuer = parts[1] if len(parts) > 1 else None
            date = parts[2] if len(parts) > 2 else None
            awards.append(Award(title=title, issuer=issuer, date=date))
        return awards
