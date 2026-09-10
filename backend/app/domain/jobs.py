from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    STORY = "STORY"
    CHARACTER = "CHARACTER"
    WORLD = "WORLD"
    SCENE = "SCENE"
    SHOT = "SHOT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    TTS = "TTS"
    LIPSYNC = "LIPSYNC"
    MUSIC = "MUSIC"
    SFX = "SFX"
    UPSCALE = "UPSCALE"
    INTERPOLATION = "INTERPOLATION"
    QC = "QC"
    BEST_TAKE = "BEST_TAKE"
    TIMELINE = "TIMELINE"
    RENDER = "RENDER"
    SUBTITLE = "SUBTITLE"
    THUMBNAIL = "THUMBNAIL"
    METADATA = "METADATA"
    PUBLISH = "PUBLISH"
    REPURPOSE = "REPURPOSE"
    BATCH = "BATCH"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class JobInput:
    parameters: dict[str, Any] = field(default_factory=dict)
    reference_asset_ids: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    deterministic: bool = False


@dataclass(slots=True)
class JobOutput:
    asset_ids: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    provider_run_id: str | None = None


@dataclass(slots=True)
class GenerationJob:
    id: str
    project_id: str
    type: JobType
    target_type: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    attempt: int = 0
    max_attempts: int = 3
    input: JobInput = field(default_factory=JobInput)
    parent_job_id: str | None = None
    target_id: str | None = None
    priority: int = 100
    provider: str | None = None
    model: str | None = None
    output: JobOutput | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = field(default_factory=utc_now)
