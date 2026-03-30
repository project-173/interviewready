"""Helpers for extracting and parsing JSON from model output text."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_payload(
    text: str,
    *,
    allow_array: bool = False,
) -> dict[str, Any] | list[Any] | None:
    """Parse JSON from raw or fenced markdown text."""
    if not text or not text.strip():
        return None

    cleaned = text.strip()
    direct = _safe_load(cleaned, allow_array=allow_array)
    if direct is not None:
        return direct

    fenced_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        cleaned,
        flags=re.IGNORECASE,
    )
    if fenced_match:
        fenced_text = fenced_match.group(1).strip()
        parsed = _safe_load(fenced_text, allow_array=allow_array)
        if parsed is None:
            parsed = _parse_balanced_json(fenced_text, allow_array=allow_array)
        if parsed is not None:
            return parsed

    parsed = _parse_balanced_json(cleaned, allow_array=allow_array)
    if parsed is not None:
        return parsed

    return None


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from text; return empty dict if unavailable."""
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
        parsed = json.loads(candidate, strict=False)
    except (TypeError, ValueError):
        return None

    if isinstance(parsed, dict):
        return parsed
    if allow_array and isinstance(parsed, list):
        return parsed
    return None


def _parse_balanced_json(
    text: str, *, allow_array: bool
) -> dict[str, Any] | list[Any] | None:
    """Parse the first balanced JSON object/array substring from text."""
    if not text:
        return None

    start_indices: list[int] = []
    for idx, ch in enumerate(text):
        if ch == "{":
            start_indices.append(idx)
        elif allow_array and ch == "[":
            start_indices.append(idx)

    for start in start_indices:
        extracted = _extract_from_start(text, start)
        if not extracted:
            continue
        parsed = _safe_load(extracted, allow_array=allow_array)
        if parsed is not None:
            return parsed

    return None


def _extract_from_start(text: str, start: int) -> str | None:
    stack: list[str] = []
    in_string = False
    escape = False

    for idx in range(start, len(text)):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in ("}", "]"):
            if not stack or ch != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return text[start : idx + 1]

    return None
