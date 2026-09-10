from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ContentBrief:
    topic: str
    language: str = "en"
    duration_seconds: int = 60
    style: str = "documentary"
    audience: str = "general"
    platform: str = "youtube"
    aspect_ratio: str = "16:9"


@dataclass(frozen=True, slots=True)
class StoryPlan:
    title: str
    logline: str
    synopsis: str
    scenes: tuple["ScenePlan", ...]


@dataclass(frozen=True, slots=True)
class ScenePlan:
    number: int
    title: str
    duration_seconds: int
    visual: str
    narration: str
    shots: tuple["ShotPlan", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ShotPlan:
    number: int
    prompt: str
    duration_seconds: int
    camera: str = "medium"
    lighting: str = "natural"
    style: str = "cinematic"
