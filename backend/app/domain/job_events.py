from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class JobEvent:
    id: str
    job_id: str
    project_id: str
    event_type: str
    status: str
    progress: float
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, job_id: str, project_id: str, event_type: str, status: str, progress: float, payload: dict[str, Any] | None = None) -> "JobEvent":
        return cls(str(uuid4()), job_id, project_id, event_type, status, max(0.0, min(1.0, progress)), payload or {})
