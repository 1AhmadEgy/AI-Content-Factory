from __future__ import annotations

import re
from typing import Callable

from ..domain.translation import TranslationRequest, TranslationResult


_TRANSLATION_CAPABILITY = "translation"
_PLACEHOLDER = re.compile(r"(\{\{.*?\}\}|\{[A-Za-z0-9_.-]+\}|%\w+)")


class TranslationProviderUnavailable(RuntimeError):
    pass


class TranslationService:
    """Translation orchestration that never overwrites source content."""

    def __init__(self, provider: Callable[[TranslationRequest], str] | None = None):
        self._provider = provider

    def translate(self, request: TranslationRequest, *, manual_text: str | None = None, provider: str | None = None, model: str | None = None, version: int = 1) -> TranslationResult:
        if not request.text.strip():
            raise ValueError("TRANSLATION_SOURCE_TEXT_EMPTY")
        if version < 1:
            raise ValueError("TRANSLATION_VERSION_INVALID")
        if request.source_language == request.target_language:
            if manual_text is not None and manual_text != request.text:
                raise ValueError("IDENTITY_TRANSLATION_MUST_MATCH_SOURCE")
            return TranslationResult.create(request, request.text, provider="identity", model=model, version=version, manual=False, metadata={"requestedProvider": provider} if provider else {})
        translated = manual_text if manual_text is not None else (self._provider(request) if self._provider else None)
        if translated is None:
            raise TranslationProviderUnavailable(_TRANSLATION_CAPABILITY)
        translated = self._validate_output(request, translated)
        metadata = {"requestedProvider": provider} if provider else {}
        return TranslationResult.create(request, translated, provider=provider or ("manual" if manual_text is not None else "provider"), model=model, version=version, manual=manual_text is not None, metadata=metadata)

    @staticmethod
    def _validate_output(request: TranslationRequest, translated: str) -> str:
        if not translated.strip():
            raise ValueError("TRANSLATION_OUTPUT_EMPTY")
        source_tokens = _PLACEHOLDER.findall(request.text)
        target_tokens = _PLACEHOLDER.findall(translated)
        if sorted(source_tokens) != sorted(target_tokens):
            raise ValueError("TRANSLATION_PLACEHOLDERS_CHANGED")
        for term in request.preserve_terms:
            if term and term not in translated:
                raise ValueError("TRANSLATION_PRESERVED_TERM_MISSING")
        return translated

    @staticmethod
    def with_provider(provider: Callable[[TranslationRequest], str]) -> "TranslationService":
        return TranslationService(provider=provider)
