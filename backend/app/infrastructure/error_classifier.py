from __future__ import annotations

import socket
import urllib.error
from enum import Enum

import httpx


class ErrorKind(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    AUTH = "auth"


TRANSIENT_STATUS = frozenset({408, 429, 500, 502, 503, 504})
AUTH_STATUS = frozenset({401, 403})


def classify_exception(exc: Exception) -> ErrorKind:
    """Normalize transport/provider failures into the worker retry contract.

    Adapters may use urllib, httpx, or standard-library network exceptions.
    Classification deliberately follows the original cause when an adapter
    wraps a transport exception in a provider-specific exception.
    """
    current: BaseException | None = exc
    visited: set[int] = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))

        if isinstance(current, httpx.TimeoutException | socket.timeout | TimeoutError):
            return ErrorKind.TRANSIENT

        if isinstance(current, (httpx.ConnectError, ConnectionError)):
            return ErrorKind.TRANSIENT

        if isinstance(current, urllib.error.HTTPError):
            status = current.code
            if status in TRANSIENT_STATUS:
                return ErrorKind.TRANSIENT
            if status in AUTH_STATUS:
                return ErrorKind.AUTH
            if 400 <= status < 500:
                return ErrorKind.PERMANENT

        if isinstance(current, httpx.HTTPStatusError):
            status = current.response.status_code
            if status in TRANSIENT_STATUS:
                return ErrorKind.TRANSIENT
            if status in AUTH_STATUS:
                return ErrorKind.AUTH
            if 400 <= status < 500:
                return ErrorKind.PERMANENT

        if isinstance(current, urllib.error.URLError):
            reason = current.reason
            if isinstance(reason, (socket.timeout, TimeoutError, ConnectionError)):
                return ErrorKind.TRANSIENT
            # A URL error is a transport failure unless it explicitly exposes
            # an HTTP status, which is handled above.
            return ErrorKind.TRANSIENT

        current = current.__cause__ or current.__context__

    return ErrorKind.PERMANENT


def classify_provider_response(error_code: str | None, error_message: str | None = None) -> ErrorKind:
    """Classify adapter failures without treating ordinary validation as outages."""
    text = f"{error_code or ''} {error_message or ''}".lower()
    if any(token in text for token in ("timeout", "timed out", "408", "429", "rate_limit", "rate limit", "500", "502", "503", "504", "temporarily unavailable")):
        return ErrorKind.TRANSIENT
    if any(token in text for token in ("401", "403", "unauthorized", "forbidden", "authentication", "invalid api key")):
        return ErrorKind.AUTH
    return ErrorKind.PERMANENT
