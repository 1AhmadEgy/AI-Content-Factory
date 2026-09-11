from __future__ import annotations

from typing import Any


class LanguageMediaService:
    """Build language-specific subtitle/TTS manifests without mutating episode source."""

    @staticmethod
    def _provenance(variant: dict[str, Any], item: dict[str, Any] | None = None) -> dict[str, Any]:
        item = item or {}
        return {
            "sourceId": item.get("sourceId") or item.get("segmentId") or variant.get("sourceId"),
            "sourceVersion": item.get("sourceVersion") or variant.get("sourceVersion"),
            "translationVersion": item.get("translationVersion") or variant.get("translationVersion") or variant.get("languagePackVersion"),
            "sourceLanguage": item.get("sourceLanguage") or variant.get("sourceLanguage"),
            "targetLanguage": item.get("targetLanguage") or variant.get("language") or variant.get("targetLanguage"),
            "contentType": item.get("contentType") or variant.get("contentType") or "dialogue",
            "sourcePreserved": True,
        }

    @staticmethod
    def subtitle_cues(variant: dict[str, Any]) -> list[dict[str, Any]]:
        cues = variant.get("subtitles") or []
        if not isinstance(cues, list):
            return []
        output: list[dict[str, Any]] = []
        for index, cue in enumerate(cues):
            if not isinstance(cue, dict) or not str(cue.get("text", "")).strip():
                continue
            normalized = dict(cue)
            normalized["index"] = normalized.get("index", index)
            normalized.update(LanguageMediaService._provenance(variant, normalized))
            output.append(normalized)
        return output

    @staticmethod
    def speech_units(variant: dict[str, Any]) -> list[dict[str, Any]]:
        units: list[dict[str, Any]] = []
        for scene in variant.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            scene_number = scene.get("number")
            for index, line in enumerate(scene.get("dialogue") or []):
                if not isinstance(line, dict) or not str(line.get("text", "")).strip():
                    continue
                unit = {
                    "sceneNumber": scene_number,
                    "index": index,
                    "text": line["text"],
                    "characterId": line.get("characterId"),
                    "speaker": line.get("speaker"),
                    "start": line.get("start"),
                    "end": line.get("end"),
                    "shotId": line.get("shotId"),
                }
                unit.update(LanguageMediaService._provenance(variant, line))
                units.append(unit)
            narration = scene.get("fields", {}).get("narration") if isinstance(scene.get("fields"), dict) else None
            if isinstance(narration, str) and narration.strip():
                unit = {
                    "sceneNumber": scene_number,
                    "index": len(units),
                    "text": narration,
                    "characterId": None,
                    "speaker": "narrator",
                    "start": scene.get("start"),
                    "end": scene.get("end"),
                    "shotId": None,
                    "contentType": "dialogue",
                }
                unit.update(LanguageMediaService._provenance(variant, unit))
                units.append(unit)
        return units

    @staticmethod
    def build_tts_manifest(variant: dict[str, Any]) -> dict[str, Any]:
        language = str(variant.get("language") or "")
        units = LanguageMediaService.speech_units(variant)
        return {
            "schemaVersion": 2,
            "language": language,
            "locale": variant.get("locale"),
            "sourceEpisodeId": variant.get("sourceEpisodeId"),
            "sourceLanguage": variant.get("sourceLanguage"),
            "translationVersion": variant.get("translationVersion") or variant.get("languagePackVersion"),
            "sourcePreserved": True,
            "units": units,
        }
