from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.jobs import JobInput, JobType
from .job_service import JobService


@dataclass(slots=True)
class OperationRequest:
    project_id: str
    type: JobType
    target_type: str
    target_id: str | None = None
    parameters: dict[str, Any] | None = None
    priority: int = 50
    max_attempts: int = 3
    provider: str | None = None
    model: str | None = None


class OperationService:
    """Small canonical entry point for creating queue-backed domain operations."""

    def __init__(self, jobs: JobService, enqueue):
        self.jobs = jobs
        self.enqueue = enqueue

    def submit(self, request: OperationRequest):
        job = self.jobs.create(
            project_id=request.project_id,
            job_type=request.type,
            target_type=request.target_type,
            target_id=request.target_id,
            priority=request.priority,
            max_attempts=request.max_attempts,
            provider=request.provider,
            model=request.model,
            input=JobInput(parameters=request.parameters or {}),
        )
        self.enqueue(job)
        return job
