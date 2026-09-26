from io import BytesIO
from urllib.error import HTTPError, URLError
from socket import timeout as SocketTimeout

from app.infrastructure.error_classifier import ErrorKind, classify_exception, classify_provider_response


def http_error(status: int) -> HTTPError:
    return HTTPError(
        url="https://provider.invalid",
        code=status,
        msg=f"HTTP {status}",
        hdrs=None,
        fp=BytesIO(b"{}"),
    )


def test_http_429_is_transient() -> None:
    assert classify_exception(http_error(429)) is ErrorKind.TRANSIENT


def test_http_5xx_is_transient() -> None:
    assert classify_exception(http_error(503)) is ErrorKind.TRANSIENT


def test_http_401_and_403_are_auth() -> None:
    assert classify_exception(http_error(401)) is ErrorKind.AUTH
    assert classify_exception(http_error(403)) is ErrorKind.AUTH


def test_http_4xx_validation_is_permanent() -> None:
    assert classify_exception(http_error(400)) is ErrorKind.PERMANENT
    assert classify_exception(http_error(404)) is ErrorKind.PERMANENT


def test_url_timeout_is_transient() -> None:
    assert classify_exception(URLError(SocketTimeout("timed out"))) is ErrorKind.TRANSIENT


def test_wrapped_http_error_preserves_classification() -> None:
    try:
        try:
            raise http_error(429)
        except HTTPError as exc:
            raise RuntimeError("OpenAIProviderError") from exc
    except RuntimeError as wrapped:
        assert classify_exception(wrapped) is ErrorKind.TRANSIENT


def test_provider_response_classification_matches_worker_contract() -> None:
    assert classify_provider_response("RATE_LIMIT", "429 too many requests") is ErrorKind.TRANSIENT
    assert classify_provider_response("AUTH_ERROR", "401 invalid api key") is ErrorKind.AUTH
    assert classify_provider_response("INVALID_REQUEST", "400 malformed request") is ErrorKind.PERMANENT
