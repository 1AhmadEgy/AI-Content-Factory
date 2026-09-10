from __future__ import annotations

from dataclasses import dataclass

from .renderer import RenderProfile


@dataclass(frozen=True, slots=True)
class RepurposeVariant:
    name: str
    profile: RenderProfile
    max_duration_s: int
    description: str


DEFAULT_REPURPOSE_VARIANTS = (
    RepurposeVariant("vertical_short", RenderProfile("vertical_1080p", 1080, 1920, 30), 60, "Shorts/Reels/TikTok"),
    RepurposeVariant("square", RenderProfile("square_1080p", 1080, 1080, 30), 90, "Square social feed"),
    RepurposeVariant("horizontal", RenderProfile("horizontal_1080p", 1920, 1080, 30), 600, "YouTube/Facebook landscape"),
)


def variants_for(duration_s: float, variants=DEFAULT_REPURPOSE_VARIANTS) -> list[RepurposeVariant]:
    return [v for v in variants if duration_s <= v.max_duration_s]
