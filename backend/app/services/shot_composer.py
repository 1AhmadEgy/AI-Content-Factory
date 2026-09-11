from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from ..domain.characters import CharacterProfile
from ..domain.locations import LocationProfile


class ShotComposer:
    """Build deterministic, provider-neutral image prompts from real project entities."""

    CAMERA_MAP = {
        "wide": "wide establishing shot",
        "medium": "medium cinematic shot",
        "close_up": "close-up portrait framing",
        "low_angle": "low-angle cinematic shot",
        "high_angle": "high-angle cinematic shot",
        "over_shoulder": "over-the-shoulder shot",
    }
    EMOTION_MAP = {
        "angry": "angry expression",
        "happy": "joyful expression",
        "determined": "determined expression",
        "smug": "confident smug expression",
        "shocked": "shocked expression",
        "sad": "sad expression",
        "calm": "calm expression",
        "fearful": "fearful expression",
    }
    MOOD_MAP = {
        "tense": "tense dramatic moment",
        "comedic": "comedic moment",
        "epic": "epic cinematic moment",
        "sad": "melancholic moment",
        "action": "high-energy action moment",
        "peaceful": "calm peaceful moment",
    }

    def compose(
        self,
        characters: Sequence[CharacterProfile],
        location: LocationProfile | None = None,
        visual_style: Mapping[str, Any] | None = None,
        *,
        camera_angle: str = "medium",
        mood: str | None = None,
        scene_context: str | None = None,
        character_actions: Mapping[str, str] | None = None,
        character_emotions: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        if not characters:
            raise ValueError("AT_LEAST_ONE_CHARACTER_REQUIRED")
        actions = character_actions or {}
        emotions = character_emotions or {}
        parts: list[str] = []

        style = dict(visual_style or {})
        if not style:
            style = dict(characters[0].visual_style)
        style_prompt = self._style_prompt(style)
        if style_prompt:
            parts.append(style_prompt)

        parts.append({1: "single character", 2: "two characters",}.get(len(characters), f"group of {len(characters)} characters"))
        for index, character in enumerate(characters, start=1):
            appearance = character.appearance
            desc: list[str] = [f"Character {index}: {character.name}"]
            if character.description:
                desc.append(character.description)
            for key in ("gender", "age", "build", "hair", "hairColor", "eyeColor", "outfit", "costume"):
                value = appearance.get(key)
                if value:
                    desc.append(f"{key}={value}")
            if character.personality:
                desc.append(f"personality={self._compact_json(character.personality)}")
            if actions.get(character.id):
                desc.append(f"action={actions[character.id]}")
            emotion = emotions.get(character.id)
            if emotion:
                desc.append(self.EMOTION_MAP.get(emotion, emotion))
            parts.append(", ".join(desc))

        if location:
            location_parts = [f"Setting: {location.name}"]
            if location.description:
                location_parts.append(location.description)
            for value in (location.geography, location.architecture, location.environment, location.lighting, location.weather):
                if value:
                    location_parts.append(self._compact_json(value))
            if location.time_of_day:
                location_parts.append(f"time={location.time_of_day}")
            if location.props:
                location_parts.append("props=" + ", ".join(location.props))
            parts.append("; ".join(location_parts))

        if mood:
            parts.append(self.MOOD_MAP.get(mood, mood))
        parts.append(self.CAMERA_MAP.get(camera_angle, camera_angle))
        if scene_context:
            parts.append(scene_context.strip())
        parts.append("consistent character identity, consistent environment identity, professional cinematic composition, highly detailed")

        negatives = [
            "low quality", "blurry", "distorted anatomy", "extra limbs", "missing fingers",
            "watermark", "text", "signature", "deformed face", "duplicate character",
        ]
        for character in characters:
            negatives.extend(character.metadata.get("negativePrompt", []) if isinstance(character.metadata.get("negativePrompt", []), list) else [])
        negative = ", ".join(dict.fromkeys(str(item) for item in negatives if str(item).strip()))
        return {"prompt": ". ".join(parts), "negative_prompt": negative}

    def continuity_hash(self, characters: Sequence[CharacterProfile], location: LocationProfile | None) -> str:
        identity = []
        for character in sorted(characters, key=lambda item: item.id):
            identity.append({"id": character.id, "version": character.version, "appearance": character.appearance, "visualStyle": character.visual_style})
        identity.append({"location": location.id if location else None, "locationVersion": location.version if location else None})
        raw = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _style_prompt(style: Mapping[str, Any]) -> str:
        values: list[str] = []
        for key in ("name", "prompt", "promptTemplate", "style", "medium", "palette", "lighting"):
            value = style.get(key)
            if value:
                values.append(str(value))
        return ", ".join(values)

    @staticmethod
    def _compact_json(value: Mapping[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
