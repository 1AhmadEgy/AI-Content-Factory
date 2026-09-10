from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..domain.translation import TranslationRequest, TranslationResult
from .translation_service import TranslationProviderUnavailable, TranslationService


@dataclass(frozen=True, slots=True)
class ContentSegment:
    """A versioned source segment used by the multilingual production pipeline."""

    id: str
    text: str
    content_type: str
    version: int = 1
    context: dict[str, Any] | None = None
    preserve_terms: tuple[str, ...] = ()


class TranslationPipeline:
    """Translate story/script/dialogue/subtitle segments without mutating source content."""

    def __init__(
        self,
        repository: Any = None,
        provider: Callable[[TranslationRequest], str] | None = None,
    ) -> None:
        self.repository = repository
        self.service = (
            TranslationService.with_provider(provider)
            if provider is not None
            else TranslationService()
        )

    def translate_segments(
        self,
        segments: list[ContentSegment],
        *,
        source_language: str,
        target_languages: list[str],
        glossary: dict[str, str] | None = None,
        provider: str | None = None,
        model: str | None = None,
        manual_texts: dict[str, dict[str, str]] | None = None,
        translation_version: int = 1,
    ) -> dict[str, Any]:
        if not segments:
            raise ValueError("TRANSLATION_SEGMENTS_EMPTY")

        targets = list(dict.fromkeys(target_languages))
        if not targets:
            raise ValueError("TRANSLATION_TARGET_LANGUAGES_EMPTY")
        if len(targets) > 20:
            raise ValueError("TRANSLATION_BATCH_TOO_LARGE")
        if translation_version < 1:
            raise ValueError("TRANSLATION_VERSION_INVALID")

        results: list[TranslationResult] = []
        errors: list[dict[str, str]] = []
        glossary = dict(glossary or {})
        manual_texts = manual_texts or {}

        for segment in segments:
            if not segment.id.strip():
                errors.extend(
                    {
                        "segmentId": segment.id,
                        "targetLanguage": target,
                        "error": "TRANSLATION_SEGMENT_ID_EMPTY",
                    }
                    for target in targets
                )
                continue
            if segment.version < 1:
                errors.extend(
                    {
                        "segmentId": segment.id,
                        "targetLanguage": target,
                        "error": "TRANSLATION_SOURCE_VERSION_INVALID",
                    }
                    for target in targets
                )
                continue

            for target in targets:
                request = TranslationRequest(
                    source_language=source_language,
                    target_language=target,
                    text=segment.text,
                    content_type=segment.content_type,
                    source_id=segment.id,
                    source_version=segment.version,
                    preserve_terms=segment.preserve_terms,
                    glossary=glossary,
                    context=dict(segment.context or {}),
                )
                manual_text = manual_texts.get(segment.id, {}).get(target)

                try:
                    # Automated results are reusable. Manual input is an explicit
                    # override and is therefore intentionally evaluated again.
                    if self.repository is not None and manual_text is None:
                        existing = self.repository.latest(request)
                        if existing is not None:
                            results.append(existing)
                            continue

                    result = self.service.translate(
                        request,
                        manual_text=manual_text,
                        provider=provider,
                        model=model,
                        version=translation_version,
                    )
                    if self.repository is not None:
                        result = self.repository.save(result, request)
                    results.append(result)
                except TranslationProviderUnavailable:
                    errors.append(
                        {
                            "segmentId": segment.id,
                            "targetLanguage": target,
                            "error": "TRANSLATION_PROVIDER_NOT_CONFIGURED",
                        }
                    )
                except ValueError as exc:
                    errors.append(
                        {
                            "segmentId": segment.id,
                            "targetLanguage": target,
                            "error": str(exc),
                        }
                    )

        return {
            "results": results,
            "errors": errors,
            "sourceLanguage": source_language,
            "targetLanguages": targets,
            "translationVersion": translation_version,
            "sourcePreserved": True,
        }
