"""Helpers for extracting and parsing JSON from model output text."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_payload(
    text: str | dict[str, Any] | list[Any],
    *,
    allow_array: bool = False,
) -> dict[str, Any] | list[Any] | None:
    """Parse JSON from raw or fenced markdown text."""
    if isinstance(text, dict):
        return text
    if isinstance(text, list):
        return text if allow_array else None
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    direct = _safe_load(cleaned, allow_array=allow_array)
    if direct is not None:
        return direct

    fenced_match = re.search(
        r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```",
        cleaned,
        flags=re.IGNORECASE,
    )
    if fenced_match:
        parsed = _safe_load(fenced_match.group(1).strip(), allow_array=allow_array)
        if parsed is not None:
            return parsed

    object_match = re.search(r"\{[\s\S]*\}", cleaned)
    if object_match:
        parsed = _safe_load(object_match.group(0).strip(), allow_array=False)
        if parsed is not None:
            return parsed

    if allow_array:
        array_match = re.search(r"\[[\s\S]*\]", cleaned)
        if array_match:
            parsed = _safe_load(array_match.group(0).strip(), allow_array=True)
            if parsed is not None:
                return parsed

    return None


def parse_json_object(text: str | dict[str, Any]) -> dict[str, Any]:
    """Parse a JSON object from text; return empty dict if unavailable."""
    if isinstance(text, dict):
        return text
    parsed = parse_json_payload(text, allow_array=False)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _safe_load(
    candidate: str,
    *,
    allow_array: bool,
) -> dict[str, Any] | list[Any] | None:
    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError):
        return None

    if isinstance(parsed, dict):
        return parsed
    if allow_array and isinstance(parsed, list):
        return parsed
    return None
