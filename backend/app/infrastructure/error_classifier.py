from __future__ import annotations

from enum import Enum

import httpx


class ErrorKind(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    AUTH = "auth"


TRANSIENT_STATUS = frozenset({408, 429, 500, 502, 503, 504})
AUTH_STATUS = frozenset({401, 403})


def classify_exception(exc: Exception) -> ErrorKind:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return ErrorKind.TRANSIENT
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in TRANSIENT_STATUS:
            return ErrorKind.TRANSIENT
        if status in AUTH_STATUS:
            return ErrorKind.AUTH
        if 400 <= status < 500:
            return ErrorKind.PERMANENT
    return ErrorKind.PERMANENT


def classify_provider_response(error_code: str | None, error_message: str | None = None) -> ErrorKind:
    """Classify adapter failures without treating ordinary validation as outages."""
    text = f"{error_code or ''} {error_message or ''}".lower()
    if any(token in text for token in ("timeout", "timed out", "408", "429", "rate_limit", "rate limit", "500", "502", "503", "504", "temporarily unavailable")):
        return ErrorKind.TRANSIENT
    if any(token in text for token in ("401", "403", "unauthorized", "forbidden", "authentication", "invalid api key")):
        return ErrorKind.AUTH
    return ErrorKind.PERMANENT
