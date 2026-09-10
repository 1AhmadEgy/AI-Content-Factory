from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContentBrief:
    topic: str
    language: str = "en"
    duration_seconds: int = 60
    style: str = "documentary"
    audience: str = "general"
    platform: str = "youtube"
    aspect_ratio: str = "16:9"
    character_ids: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
    continuity_rules: tuple[str, ...] = ()
    country_id: str = "egypt"
    library_id: str = "local-library-egypt"
    dialect: str | None = None
    glossary: dict[str, str] = field(default_factory=dict)
    production_context: dict[str, Any] = field(default_factory=dict)
    project_id: str | None = None


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
    character_ids: tuple[str, ...] = ()
    location_ids: tuple[str, ...] = ()
