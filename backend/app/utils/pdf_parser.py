"""PDF parsing utilities for resume processing."""

import base64
import re
from typing import Optional, Dict, Any
import io

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from ..core.logging import logger


def is_pdf_data(job_description: str) -> bool:
    """Check if job description contains PDF file data.

    Args:
        job_description: Job description string that might contain file data

    Returns:
        True if PDF data is detected
    """
    if not job_description:
        return False

    # Check for PDF file patterns
    pdf_indicators = [
        "file data:",
        "mime type: application/pdf",
        "data:application/pdf",
        "pdf file",
        "base64 pdf",
    ]

    lower_desc = job_description.lower()
    return any(indicator in lower_desc for indicator in pdf_indicators)


def extract_base64_from_text(text: str) -> Optional[str]:
    """Extract base64 data from text that contains file information.

    Args:
        text: Text containing base64 file data

    Returns:
        Base64 string if found, None otherwise
    """
    # Look for base64 patterns (typically long strings of base64 characters)
    base64_pattern = r"[A-Za-z0-9+/]{100,}={0,2}"
    matches = re.findall(base64_pattern, text)

    if matches:
        # Return the longest match (most likely to be the actual file data)
        return max(matches, key=len)

    return None


def parse_pdf_base64(base64_data: str) -> Optional[str]:
    """Parse PDF from base64 encoded data.

    Args:
        base64_data: Base64 encoded PDF data

    Returns:
        Extracted text content if successful, None otherwise
    """
    if not PYPDF_AVAILABLE:
        logger.warning("pypdf not available, cannot parse PDF")
        return None

    try:
        pdf_bytes = base64.b64decode(base64_data)
        pdf_file = io.BytesIO(pdf_bytes)

        reader = PdfReader(pdf_file)
        text_content = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content += text + "\n"

        if text_content.strip():
            logger.info(
                "Successfully parsed PDF",
                pages=len(reader.pages),
                text_length=len(text_content),
            )
            return text_content.strip()
        else:
            logger.warning("PDF parsed but no text content found")
            return None

    except Exception as e:
        logger.error("Failed to parse PDF", error=str(e), error_type=type(e).__name__)
        return None


def process_pdf_input(job_description: str) -> Optional[str]:
    """Process job description that contains PDF data and return extracted text.

    Args:
        job_description: Job description string that might contain PDF data

    Returns:
        Extracted text if PDF is successfully parsed, None otherwise
    """
    if not is_pdf_data(job_description):
        return None

    logger.info("PDF data detected in input", input_length=len(job_description))

    # Extract base64 data
    base64_data = extract_base64_from_text(job_description)
    if not base64_data:
        logger.error("Could not extract base64 data from PDF input")
        return None

    logger.info("Extracted base64 data", data_length=len(base64_data))

    # Parse PDF
    extracted_text = parse_pdf_base64(base64_data)
    if extracted_text:
        logger.info("PDF parsing successful", extracted_text_length=len(extracted_text))
        return extracted_text
    else:
        logger.error("PDF parsing failed")
        return None


def create_pdf_processing_prompt(extracted_text: str) -> str:
    """Create a prompt for processing extracted PDF text.

    Args:
        extracted_text: Text extracted from PDF

    Returns:
        Formatted prompt for resume processing
    """
    return f"""Parse and analyze this resume text extracted from PDF:

{extracted_text}

Please extract the resume data and provide a structured critique in JSON format with:
- resume_data: Structured resume information
- critique: Formatting and content analysis

Focus on ATS compatibility, structure, and overall impact."""
