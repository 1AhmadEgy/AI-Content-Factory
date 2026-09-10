from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ProviderRun:
    job_id: str
    provider: str
    model: str | None = None
    status: str = "RUNNING"
    request_metadata: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_code: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def complete(self, status: str = "COMPLETED", *, error_code: str | None = None) -> None:
        self.status = status
        self.error_code = error_code
        self.completed_at = utc_now()
        self.duration_ms = max(0, int((self.completed_at - self.started_at).total_seconds() * 1000))
