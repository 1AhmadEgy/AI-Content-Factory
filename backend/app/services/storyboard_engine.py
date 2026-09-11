from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..domain.content import ContentBrief
from ..domain.storyboard import CameraAngle, Scene, Shot, ShotType, Storyboard


class StoryboardGenerationError(RuntimeError):
    """Raised when storyboard generation cannot produce a valid plan."""


@dataclass(frozen=True, slots=True)
class StoryboardRequest:
    script_text: str
    project_id: str
    style_preset: str = "cinematic"
    target_duration_seconds: float = 60.0


Planner = Callable[[str, Mapping[str, Any]], list[Mapping[str, Any]]]


class StoryboardEngine:
    """Provider-agnostic storyboard planner with deterministic local parsing.

    An optional planner may return schema-shaped scene data from a real LLM provider.
    No synthetic media is produced here; this layer only creates editorial intent.
    """

    def __init__(self, planner: Planner | None = None) -> None:
        self._planner = planner

    def generate(self, request: StoryboardRequest) -> Storyboard:
        script = request.script_text.strip()
        if not script:
            raise StoryboardGenerationError("script_text must not be empty")
        if request.target_duration_seconds <= 0:
            raise StoryboardGenerationError("target_duration_seconds must be positive")

        raw_scenes = self._planner(script, {
            "style_preset": request.style_preset,
            "target_duration_seconds": request.target_duration_seconds,
        }) if self._planner else self._parse_script(script)

        scenes = tuple(self._build_scene(i, item, request.style_preset) for i, item in enumerate(raw_scenes, 1))
        storyboard = Storyboard(
            storyboard_id=self._stable_id(request.project_id, script, request.style_preset),
            project_id=request.project_id,
            style_preset=request.style_preset,
            target_duration_seconds=request.target_duration_seconds,
            scenes=scenes,
        )
        errors = storyboard.validate()
        if errors:
            raise StoryboardGenerationError("; ".join(errors))
        return storyboard

    def regenerate_scene(self, storyboard: Storyboard, scene_id: str, scene_data: Mapping[str, Any]) -> Storyboard:
        if not any(scene.scene_id == scene_id for scene in storyboard.scenes):
            raise StoryboardGenerationError(f"unknown scene_id: {scene_id}")
        replacement = self._build_scene(
            next(scene.index for scene in storyboard.scenes if scene.scene_id == scene_id),
            scene_data,
            storyboard.style_preset,
            scene_id=scene_id,
        )
        scenes = tuple(replacement if scene.scene_id == scene_id else scene for scene in storyboard.scenes)
        result = Storyboard(
            storyboard.storyboard_id,
            storyboard.project_id,
            storyboard.style_preset,
            storyboard.target_duration_seconds,
            scenes,
            storyboard.schema_version,
            {**storyboard.metadata, "last_regenerated_scene": scene_id},
        )
        errors = result.validate()
        if errors:
            raise StoryboardGenerationError("; ".join(errors))
        return result

    def _build_scene(self, index: int, data: Mapping[str, Any], style: str, scene_id: str | None = None) -> Scene:
        sid = scene_id or f"scene-{index:03d}"
        setting = str(data.get("setting", "unspecified setting")).strip()
        characters = tuple(str(x) for x in data.get("characters", ()) if str(x).strip())
        action = str(data.get("action", "")).strip() or "The scene develops the story."
        dialogue = str(data.get("dialogue", "")).strip()
        mood = str(data.get("mood", "")).strip()
        raw_shots = data.get("shots") or [{"prompt": f"{action} in {setting}", "duration_seconds": 4}]
        shots = tuple(self._build_shot(index, n, shot, sid, characters, style) for n, shot in enumerate(raw_shots, 1))
        return Scene(sid, index, setting, characters, action, dialogue, mood, shots)

    def _build_shot(self, scene_index: int, shot_index: int, data: Mapping[str, Any], scene_id: str, characters: tuple[str, ...], style: str) -> Shot:
        shot_id = f"{scene_id}-shot-{shot_index:02d}"
        prompt = str(data.get("prompt", "")).strip() or "cinematic establishing shot"
        duration = float(data.get("duration_seconds", 4))
        shot_type = self._enum(ShotType, data.get("shot_type", "medium"), ShotType.MEDIUM)
        angle = self._enum(CameraAngle, data.get("camera_angle", "eye-level"), CameraAngle.EYE_LEVEL)
        return Shot(shot_id, scene_id, shot_type, angle, prompt, duration, characters, metadata={"style": style})

    @staticmethod
    def _enum(enum_type: type, value: Any, default: Any) -> Any:
        try:
            return enum_type(str(value))
        except ValueError:
            return default

    @staticmethod
    def _parse_script(script: str) -> list[dict[str, Any]]:
        markers = re.split(r"(?im)(?=^(?:INT\.|EXT\.|INT/EXT\.|SCENE\b))", script)
        chunks = [chunk.strip() for chunk in markers if chunk.strip()]
        if not chunks:
            chunks = [script]
        result: list[dict[str, Any]] = []
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            setting = lines[0] if lines else "unspecified setting"
            action = " ".join(lines[1:]) if len(lines) > 1 else chunk
            result.append({"setting": setting, "action": action, "characters": (), "shots": [{"prompt": action[:500], "duration_seconds": 4}]})
        return result

    @staticmethod
    def _stable_id(project_id: str, script: str, style: str) -> str:
        digest = hashlib.sha256(f"{project_id}\n{style}\n{script}".encode()).hexdigest()[:16]
        return f"storyboard-{digest}"


def storyboard_request_from_brief(brief: ContentBrief, script_text: str) -> StoryboardRequest:
    return StoryboardRequest(
        script_text=script_text,
        project_id=brief.project_id or "unassigned",
        style_preset=brief.style,
        target_duration_seconds=float(brief.duration_seconds),
    )
