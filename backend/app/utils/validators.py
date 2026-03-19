"""Validation utilities for resume data."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse


DATE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?$")


def is_valid_date(date_str: Optional[str]) -> bool:
    """Check if a date string is in valid format (yyyy-mm-dd, yyyy-mm, or empty).

    Args:
        date_str: Date string to validate

    Returns:
        True if valid format, False otherwise
    """
    if date_str is None or date_str == "":
        return True
    return bool(DATE_PATTERN.match(date_str))


def is_valid_url(url: Optional[str]) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid, False otherwise
    """
    if url is None or url == "":
        return True
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in (
            "http",
            "https",
        )
    except Exception:
        return False


def is_full_url(url: str) -> bool:
    """Check if URL is a full URL (not a domain or partial string).

    Args:
        url: URL string to check

    Returns:
        True if it's a full URL with http/https scheme
    """
    return url.startswith("http://") or url.startswith("https://")
