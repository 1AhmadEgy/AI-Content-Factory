from fastapi import Header, HTTPException, status
from os import getenv
from secrets import compare_digest


PUBLIC_PATHS = {"/health", "/ready"}


def configured_api_key() -> str:
    return getenv("AICF_API_KEY", "").strip()


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = configured_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend API key is not configured",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = authorization[7:].strip()
    if not supplied or not compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
