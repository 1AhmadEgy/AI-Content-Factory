from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    source_language: str
    target_language: str
    text: str
    content_type: str = "text"
    source_id: str | None = None
    preserve_terms: tuple[str, ...] = ()
    glossary: dict[str, str] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    requested_by: str | None = None

    def idempotency_key(self) -> str:
        import hashlib
        payload = "\x1f".join((self.source_language, self.target_language, self.content_type, self.source_id or "", self.text))
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
        return cls(id=f"tr_{uuid4().hex}", source_language=request.source_language, target_language=request.target_language, source_text=request.text, translated_text=translated_text, content_type=request.content_type, source_id=request.source_id, provider=provider, model=model, version=version, manual=manual, metadata=dict(metadata or {}))
