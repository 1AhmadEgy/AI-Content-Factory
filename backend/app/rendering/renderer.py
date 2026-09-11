from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..domain.timeline import Timeline


@dataclass(frozen=True, slots=True)
class RenderProfile:
    name: str = "vertical_1080p"
    width: int = 1080
    height: int = 1920
    fps: float = 30.0
    video_codec: str = "h264"
    audio_codec: str = "aac"
    container: str = "mp4"


@dataclass(frozen=True, slots=True)
class RenderResult:
    success: bool
    output_path: str | None = None
    error: str | None = None


class Renderer(ABC):
    @abstractmethod
    def validate(self, timeline: Timeline, profile: RenderProfile) -> list[str]: ...

    @abstractmethod
    def render(self, timeline: Timeline, profile: RenderProfile, output_path: str) -> RenderResult: ...
