from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import hashlib


TRANSLATABLE_CONTENT_TYPES = ("story", "script", "dialogue", "title", "metadata", "subtitle")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    source_language: str
    target_language: str
    text: str
    content_type: str = "dialogue"
    source_id: str | None = None
    source_version: int = 1
    preserve_terms: tuple[str, ...] = ()
    glossary: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    requested_by: str | None = None

    def __post_init__(self) -> None:
        if not self.source_language.strip() or not self.target_language.strip():
            raise ValueError("TRANSLATION_LANGUAGE_REQUIRED")
        if not self.text.strip():
            raise ValueError("TRANSLATION_SOURCE_TEXT_EMPTY")
        if self.content_type not in TRANSLATABLE_CONTENT_TYPES:
            raise ValueError("TRANSLATION_CONTENT_TYPE_UNSUPPORTED")
        if self.source_version < 1:
            raise ValueError("TRANSLATION_SOURCE_VERSION_INVALID")

    def idempotency_key(self) -> str:
        payload = "\x1f".join((self.source_language, self.target_language, self.content_type, self.source_id or "", str(self.source_version), self.text))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TranslationResult:
    id: str
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    content_type: str
    source_id: str | None = None
    provider: str = "local"
    model: str | None = None
    glossary_version: int = 1
    version: int = 1
    manual: bool = False
    created_at: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, request: TranslationRequest, translated_text: str, *, provider: str = "local", model: str | None = None, version: int = 1, manual: bool = False, metadata: dict[str, Any] | None = None) -> "TranslationResult":
        if version < 1:
            raise ValueError("TRANSLATION_VERSION_INVALID")
        return cls(id=f"tr_{uuid4().hex}", source_language=request.source_language, target_language=request.target_language, source_text=request.text, translated_text=translated_text, content_type=request.content_type, source_id=request.source_id, provider=provider, model=model, version=version, manual=manual, metadata=dict(metadata or {}))
