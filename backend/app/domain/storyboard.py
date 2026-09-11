from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ShotType(str, Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close-up"
    EXTREME_CLOSE_UP = "extreme-close-up"


class CameraAngle(str, Enum):
    EYE_LEVEL = "eye-level"
    HIGH = "high"
    LOW = "low"
    DUTCH = "dutch"


@dataclass(frozen=True, slots=True)
class Shot:
    shot_id: str
    scene_id: str
    shot_type: ShotType
    camera_angle: CameraAngle
    prompt: str
    duration_seconds: float
    character_ids: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
    continuity_notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.shot_id or not self.scene_id:
            raise ValueError("shot_id and scene_id are required")
        if not self.prompt.strip():
            raise ValueError("shot prompt must not be empty")
        if not 2 <= self.duration_seconds <= 10:
            raise ValueError("shot duration must be between 2 and 10 seconds")


@dataclass(frozen=True, slots=True)
class Scene:
    scene_id: str
    index: int
    setting: str
    characters: tuple[str, ...]
    action: str
    dialogue: str = ""
    mood: str = ""
    shots: tuple[Shot, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scene_id or self.index < 1:
            raise ValueError("scene_id and positive scene index are required")
        if not self.setting.strip():
            raise ValueError("scene setting must not be empty")


@dataclass(frozen=True, slots=True)
class Storyboard:
    storyboard_id: str
    project_id: str
    style_preset: str
    target_duration_seconds: float
    scenes: tuple[Scene, ...]
    schema_version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_duration_seconds(self) -> float:
        return sum(shot.duration_seconds for scene in self.scenes for shot in scene.shots)

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        seen_scene_ids: set[str] = set()
        seen_shot_ids: set[str] = set()
        previous_scene: Scene | None = None
        for scene in self.scenes:
            if scene.scene_id in seen_scene_ids:
                errors.append(f"duplicate scene_id: {scene.scene_id}")
            seen_scene_ids.add(scene.scene_id)
            if previous_scene and not scene.setting.strip():
                errors.append(f"scene {scene.scene_id} has no setting")
            for shot in scene.shots:
                if shot.shot_id in seen_shot_ids:
                    errors.append(f"duplicate shot_id: {shot.shot_id}")
                seen_shot_ids.add(shot.shot_id)
                if shot.scene_id != scene.scene_id:
                    errors.append(f"shot {shot.shot_id} references wrong scene")
            previous_scene = scene
        if not self.scenes:
            errors.append("storyboard must contain at least one scene")
        if self.target_duration_seconds <= 0:
            errors.append("target_duration_seconds must be positive")
        return tuple(errors)
