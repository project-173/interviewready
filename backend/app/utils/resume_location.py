"""Helpers for validating resume JSON locations."""

from __future__ import annotations

import re
from typing import Any, Iterable

_TOKEN_PATTERN = re.compile(r"([^[.\]]+)|\[(\d+)\]")


def _parse_location_tokens(location: str) -> list[str | int]:
    tokens: list[str | int] = []
    for match in _TOKEN_PATTERN.finditer(location):
        key = match.group(1)
        index = match.group(2)
        if key is not None:
            tokens.append(key)
        elif index is not None:
            tokens.append(int(index))
    return tokens


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float, bool)):
        return True
    if isinstance(value, list):
        return any(_has_meaningful_value(item) for item in value) if value else False
    if isinstance(value, dict):
        return bool(value)
    return False


def resume_location_exists(resume_data: Any, location: str) -> bool:
    """Return True when location resolves to a meaningful value in resume data."""
    if not resume_data or not isinstance(location, str) or not location.strip():
        return False

    tokens = _parse_location_tokens(location)
    if not tokens:
        return False

    current: Any = resume_data
    for token in tokens:
        if isinstance(token, str):
            if not isinstance(current, dict) or token not in current:
                return False
            current = current[token]
        else:
            if not isinstance(current, list) or token < 0 or token >= len(current):
                return False
            current = current[token]

    return _has_meaningful_value(current)


def filter_locations(
    resume_data: Any, locations: Iterable[str] | None
) -> list[str]:
    if not locations:
        return []
    return [loc for loc in locations if resume_location_exists(resume_data, loc)]
