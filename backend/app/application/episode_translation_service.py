from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from ..domain.translation import TranslationRequest, TranslationResult
from .translation_service import TranslationProviderUnavailable, TranslationService


# Only spoken/editorial text is translated here. Visual generation prompts, IDs,
# timings and continuity facts remain source-of-truth production data.
_TRANSLATABLE_FIELDS = (
    ("title", "title"),
    ("logline", "story"),
    ("synopsis", "story"),
)


class EpisodeTranslationService:
    """Create immutable language variants of an episode snapshot.

    The source episode is never modified. Every translatable unit gets a stable
    sourceId, making retries idempotent while preserving production identity.
    """

    def __init__(self, translator: TranslationService | None = None, repository: Any | None = None) -> None:
        self.translator = translator or TranslationService()
        self.repository = repository

    def translate_episode(
        self,
        snapshot: dict[str, Any],
        target_languages: Iterable[str],
        *,
        manual_texts: dict[str, str] | None = None,
        version: int = 1,
    ) -> dict[str, Any]:
        source = deepcopy(snapshot)
        source_language = str(source.get("sourceLanguage") or source.get("language") or "")
        if not source_language:
            raise ValueError("EPISODE_SOURCE_LANGUAGE_REQUIRED")
        if version < 1:
            raise ValueError("TRANSLATION_VERSION_INVALID")

        targets = list(dict.fromkeys(str(item) for item in target_languages if str(item).strip()))
        if not targets:
            raise ValueError("TRANSLATION_TARGET_LANGUAGES_REQUIRED")

        episode_id = str(source.get("episodeId") or source.get("episodeNumber") or "episode")
        glossary = dict(source.get("glossary") or {})
        preserve_terms = tuple(str(item) for item in source.get("translationPolicy", {}).get("preserveTerms", []) if str(item))
        manual_texts = dict(manual_texts or {})
        variants: dict[str, dict[str, Any]] = {}
        results: list[TranslationResult] = []
        errors: list[dict[str, str]] = []

        for target in targets:
            variants[target] = self._translate_variant(source, source_language, target, episode_id, glossary, preserve_terms, manual_texts, version, results, errors)

        return {
            "source": source,
            "sourceLanguage": source_language,
            "targetLanguages": targets,
            "variants": variants,
            "translations": results,
            "errors": errors,
            "sourcePreserved": True,
            "immutableSource": True,
            "languagePackVersion": version,
        }

    def _translate_variant(self, source: dict[str, Any], source_language: str, target: str, episode_id: str, glossary: dict[str, str], preserve_terms: tuple[str, ...], manual_texts: dict[str, str], version: int, results: list[TranslationResult], errors: list[dict[str, str]]) -> dict[str, Any]:
        variant: dict[str, Any] = {
            "language": target,
            "locale": source.get("dialect") if target == source_language else None,
            "sourceEpisodeId": episode_id,
            "sourceContextVersion": source.get("contextVersion"),
            "sourcePreserved": True,
            "fields": {},
            "scenes": [],
            "subtitles": [],
        }

        for field_name, content_type in _TRANSLATABLE_FIELDS:
            text = source.get(field_name)
            if isinstance(text, str) and text.strip():
                translated = self._translate_field(text, source_language, target, content_type, f"{episode_id}:{field_name}", source, glossary, preserve_terms, manual_texts.get(f"{target}:{field_name}"), version, results, errors)
                if translated is not None:
                    variant["fields"][field_name] = translated

        raw_scenes = source.get("scenes") or []
        if isinstance(raw_scenes, list):
            for index, scene in enumerate(raw_scenes):
                if not isinstance(scene, dict):
                    continue
                scene_number = scene.get("number", index + 1)
                translated_scene = {
                    "number": scene_number,
                    "sourceSceneNumber": scene_number,
                    "fields": {},
                    # Production identity is copied, never translated or regenerated.
                    "shots": deepcopy(scene.get("shots", [])),
                    "dialogue": [],
                }
                for field_name, content_type in (("title", "title"), ("narration", "dialogue")):
                    text = scene.get(field_name)
                    if not isinstance(text, str) or not text.strip():
                        continue
                    translated = self._translate_field(text, source_language, target, content_type, f"{episode_id}:scene:{scene_number}:{field_name}", source, glossary, preserve_terms, manual_texts.get(f"{target}:scene:{scene_number}:{field_name}"), version, results, errors)
                    if translated is not None:
                        translated_scene["fields"][field_name] = translated

                raw_dialogue = scene.get("dialogue")
                if isinstance(raw_dialogue, list):
                    for dialogue_index, line in enumerate(raw_dialogue):
                        if not isinstance(line, dict):
                            continue
                        translated_line = deepcopy(line)
                        text = line.get("text")
                        if isinstance(text, str) and text.strip():
                            source_id = f"{episode_id}:scene:{scene_number}:dialogue:{dialogue_index}"
                            translated = self._translate_field(text, source_language, target, "dialogue", source_id, source, glossary, preserve_terms, manual_texts.get(f"{target}:scene:{scene_number}:dialogue:{dialogue_index}"), version, results, errors)
                            if translated is not None:
                                translated_line["text"] = translated
                        # Speaker, characterId, timing and shot references are immutable.
                        translated_scene["dialogue"].append(translated_line)
                variant["scenes"].append(translated_scene)

        raw_subtitles = source.get("subtitles") or source.get("subtitleCues") or []
        if isinstance(raw_subtitles, list):
            for cue_index, cue in enumerate(raw_subtitles):
                if not isinstance(cue, dict):
                    continue
                translated_cue = deepcopy(cue)
                text = cue.get("text")
                if isinstance(text, str) and text.strip():
                    source_id = f"{episode_id}:subtitle:{cue_index}"
                    translated = self._translate_field(text, source_language, target, "subtitle", source_id, source, glossary, preserve_terms, manual_texts.get(f"{target}:subtitle:{cue_index}"), version, results, errors)
                    if translated is not None:
                        translated_cue["text"] = translated
                # Keep start/end, cue id, speaker and shot/scene references unchanged.
                variant["subtitles"].append(translated_cue)

        return variant

    def _translate_field(self, text: str, source_language: str, target: str, content_type: str, source_id: str, source: dict[str, Any], glossary: dict[str, str], preserve_terms: tuple[str, ...], manual_text: str | None, version: int, results: list[TranslationResult], errors: list[dict[str, str]]) -> str | None:
        request = TranslationRequest(
            source_language=source_language,
            target_language=target,
            text=text,
            content_type=content_type,
            source_id=source_id,
            source_version=int(source.get("contextVersion") or 1),
            preserve_terms=preserve_terms,
            glossary=glossary,
            context={
                "countryId": source.get("countryId"),
                "libraryId": source.get("libraryId"),
                "dialect": source.get("dialect"),
                "seriesId": source.get("seriesId"),
                "episodeId": source.get("episodeId"),
            },
        )
        if self.repository is not None and manual_text is None:
            existing = self.repository.latest(request)
            if existing is not None:
                results.append(existing)
                return existing.translated_text
        try:
            result = self.translator.translate(request, manual_text=manual_text, version=version)
            if self.repository is not None:
                self.repository.save(result, request)
            results.append(result)
            return result.translated_text
        except TranslationProviderUnavailable:
            errors.append({"sourceId": source_id, "targetLanguage": target, "error": "TRANSLATION_PROVIDER_NOT_CONFIGURED"})
        except ValueError as exc:
            errors.append({"sourceId": source_id, "targetLanguage": target, "error": str(exc)})
        return None
