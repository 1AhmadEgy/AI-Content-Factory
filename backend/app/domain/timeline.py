from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrackType(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DIALOGUE = "DIALOGUE"
    MUSIC = "MUSIC"
    SFX = "SFX"
    SUBTITLE = "SUBTITLE"


@dataclass(frozen=True, slots=True)
class TimelineClip:
    id: str
    asset_id: str
    start_us: int
    duration_us: int
    source_start_us: int = 0
    z_index: int = 0

    @property
    def end_us(self) -> int:
        return self.start_us + self.duration_us


@dataclass(slots=True)
class TimelineTrack:
    id: str
    type: TrackType
    clips: list[TimelineClip] = field(default_factory=list)


@dataclass(slots=True)
class Timeline:
    id: str
    project_id: str
    duration_us: int
    timebase: int = 1_000_000
    tracks: list[TimelineTrack] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.duration_us <= 0:
            errors.append("TIMELINE_DURATION_INVALID")
        if self.timebase <= 0:
            errors.append("TIMEBASE_INVALID")
        for track in self.tracks:
            for clip in track.clips:
                if clip.start_us < 0:
                    errors.append(f"CLIP_START_NEGATIVE:{clip.id}")
                if clip.duration_us <= 0:
                    errors.append(f"CLIP_DURATION_INVALID:{clip.id}")
                if clip.end_us > self.duration_us:
                    errors.append(f"CLIP_OUT_OF_BOUNDS:{clip.id}")
        return errors
