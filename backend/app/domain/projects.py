from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Project:
    id: str
    name: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Episode:
    id: str
    project_id: str
    title: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Scene:
    id: str
    episode_id: str
    title: str
    order_index: int
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Shot:
    id: str
    scene_id: str
    order_index: int
    prompt: str = ""
    created_at: datetime = field(default_factory=utc_now)
