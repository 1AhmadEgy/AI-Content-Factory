from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaOutput:
    """Binary media returned by a provider adapter before persistence."""

    data: bytes
    mime_type: str
    filename: str | None = None
    metadata: dict[str, Any] | None = None


def media_mime(job_type: str, parameters: dict[str, Any]) -> str:
    explicit = parameters.get("mime_type") or parameters.get("mimeType")
    if isinstance(explicit, str) and explicit:
        return explicit
    return {
        "IMAGE": "image/png",
        "VIDEO": "video/mp4",
        "TTS": "audio/wav",
        "MUSIC": "audio/wav",
        "SFX": "audio/wav",
        "LIPSYNC": "video/mp4",
        "THUMBNAIL": "image/png",
        "SUBTITLE": "text/vtt; charset=utf-8",
    }.get(job_type, "application/octet-stream")
