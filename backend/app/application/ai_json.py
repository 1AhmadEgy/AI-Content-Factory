from __future__ import annotations

import json
from typing import Any


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Parse strict JSON or recover a JSON object embedded in model prose."""
    value = _decode(text.strip())
    if isinstance(value, dict):
        return value
    return None


def parse_json_array(text: str) -> list[Any] | None:
    """Parse strict JSON or recover a JSON array embedded in model prose."""
    value = _decode(text.strip())
    if isinstance(value, list):
        return value
    return None


def _decode(text: str) -> Any:
    if not text:
        return None
    candidates = [text]
    if "```" in text:
        for block in text.split("```")[1::2]:
            cleaned = block.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].lstrip("\n ")
            candidates.append(cleaned)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None
