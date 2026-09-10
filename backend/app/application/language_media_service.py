from __future__ import annotations

from typing import Any


class LanguageMediaService:
    """Build language-specific subtitle/TTS manifests without mutating episode source."""

    @staticmethod
    def subtitle_cues(variant: dict[str, Any]) -> list[dict[str, Any]]:
        cues = variant.get("subtitles") or []
        if not isinstance(cues, list):
            return []
        return [dict(cue) for cue in cues if isinstance(cue, dict) and str(cue.get("text", "")).strip()]

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
                units.append(unit)
            narration = scene.get("fields", {}).get("narration") if isinstance(scene.get("fields"), dict) else None
            if isinstance(narration, str) and narration.strip():
                units.append({
                    "sceneNumber": scene_number,
                    "index": len(units),
                    "text": narration,
                    "characterId": None,
                    "speaker": "narrator",
                    "start": scene.get("start"),
                    "end": scene.get("end"),
                    "shotId": None,
                })
        return units

    @staticmethod
    def build_tts_manifest(variant: dict[str, Any]) -> dict[str, Any]:
        language = str(variant.get("language") or "")
        return {
            "schemaVersion": 1,
            "language": language,
            "locale": variant.get("locale"),
            "sourceEpisodeId": variant.get("sourceEpisodeId"),
            "sourcePreserved": True,
            "units": LanguageMediaService.speech_units(variant),
        }
