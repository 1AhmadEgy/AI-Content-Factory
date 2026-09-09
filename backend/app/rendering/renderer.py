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


class DeterministicMockRenderer(Renderer):
    """Writes a deterministic render manifest instead of invoking FFmpeg."""

    def validate(self, timeline: Timeline, profile: RenderProfile) -> list[str]:
        errors = timeline.validate()
        if profile.width <= 0 or profile.height <= 0:
            errors.append("RENDER_DIMENSIONS_INVALID")
        if profile.fps <= 0:
            errors.append("RENDER_FPS_INVALID")
        return errors

    def render(self, timeline: Timeline, profile: RenderProfile, output_path: str) -> RenderResult:
        errors = self.validate(timeline, profile)
        if errors:
            return RenderResult(False, error=";".join(errors))
        from pathlib import Path
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest = (
            f"AI_CONTENT_FACTORY_MOCK_RENDER\n"
            f"timeline={timeline.id}\n"
            f"duration_us={timeline.duration_us}\n"
            f"profile={profile.name}\n"
            f"resolution={profile.width}x{profile.height}\n"
            f"fps={profile.fps}\n"
            f"codec={profile.video_codec}/{profile.audio_codec}\n"
        )
        path.write_text(manifest, encoding="utf-8")
        return RenderResult(True, output_path=str(path))
