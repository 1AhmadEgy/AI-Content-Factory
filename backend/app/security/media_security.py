from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path


ALLOWED_SUBTITLE_SUFFIXES = {".srt", ".vtt"}


def safe_child(root: str, requested: str) -> Path:
    """Resolve an untrusted media path without permitting traversal outside root."""
    root_path = Path(root).resolve()
    candidate = (root_path / requested).resolve()
    if candidate != root_path and root_path not in candidate.parents:
        raise ValueError("PATH_TRAVERSAL_BLOCKED")
    return candidate


def validate_subtitle_path(root: str, requested: str) -> Path:
    path = safe_child(root, requested)
    if path.suffix.lower() not in ALLOWED_SUBTITLE_SUFFIXES:
        raise ValueError("SUBTITLE_FORMAT_NOT_ALLOWED")
    return path


def asset_digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_digest(path: str, expected: str) -> bool:
    return hmac.compare_digest(asset_digest(path), expected)


def signed_token(payload: str, secret: str | None = None) -> str:
    key = (secret or os.environ.get("ACF_SIGNING_SECRET", "dev-only-change-me")).encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
