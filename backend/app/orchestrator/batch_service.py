from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from ..domain.repositories import JobRepository
from .job_service import JobService


@dataclass(slots=True)
class BatchItem:
    type: JobType
    target_type: str
    target_id: str | None = None
    input: JobInput | None = None
    priority: int = 100
    max_attempts: int = 3
    provider: str | None = None
    model: str | None = None


class BatchService:
    def __init__(self, repository: JobRepository, enqueue, context_provider: Callable[[str], dict] | None = None):
        self.repository = repository
        self.jobs = JobService(repository, context_provider=context_provider)
        self.enqueue = enqueue

    def create(self, project_id: str, items: list[BatchItem], priority: int = 100) -> GenerationJob:
        if not items:
            raise ValueError("BATCH_ITEMS_REQUIRED")
        parent = self.jobs.create(project_id=project_id, job_type=JobType.BATCH, target_type="batch",
                                  priority=priority, max_attempts=1,
                                  input=JobInput(parameters={"itemCount": len(items)}))
        for item in items:
            child = self.jobs.create(project_id=project_id, job_type=item.type,
                                     target_type=item.target_type, target_id=item.target_id,
                                     parent_job_id=parent.id, priority=item.priority,
                                     max_attempts=item.max_attempts, provider=item.provider,
                                     model=item.model, input=item.input or JobInput())
            self.enqueue(child)
        return parent

    def children(self, batch_id: str) -> list[GenerationJob]:
        return self.repository.list_by_parent(batch_id)

    def summary(self, batch_id: str) -> dict[str, Any]:
        parent = self.repository.get(batch_id)
        if not parent or parent.type is not JobType.BATCH:
            raise KeyError("BATCH_NOT_FOUND")
        children = self.children(batch_id)
        total = len(children)
        completed = sum(j.status is JobStatus.COMPLETED for j in children)
        failed = sum(j.status is JobStatus.FAILED for j in children)
        cancelled = sum(j.status is JobStatus.CANCELLED for j in children)
        running = sum(j.status is JobStatus.RUNNING for j in children)
        paused = sum(j.status is JobStatus.PAUSED for j in children)
        progress = (sum(j.progress for j in children) / total) if total else 0.0
        if total and completed == total:
            state = JobStatus.COMPLETED
        elif failed:
            state = JobStatus.FAILED
        elif cancelled == total and total:
            state = JobStatus.CANCELLED
        elif running or paused or completed:
            state = JobStatus.RUNNING
        else:
            state = JobStatus.QUEUED

        now = datetime.now(timezone.utc)
        previous = parent.status
        parent.status = state
        parent.progress = max(0.0, min(1.0, progress))
        parent.updated_at = now
        if state in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            parent.completed_at = parent.completed_at or now
        elif previous in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            parent.completed_at = None
        self.repository.update(parent)
        return {"batchId": batch_id, "status": state.value, "progress": parent.progress,
                "total": total, "completed": completed, "failed": failed, "cancelled": cancelled,
                "running": running, "paused": paused, "children": children}

    def cancel(self, batch_id: str) -> dict[str, Any]:
        parent = self.repository.get(batch_id)
        if not parent or parent.type is not JobType.BATCH:
            raise KeyError("BATCH_NOT_FOUND")
        for child in self.children(batch_id):
            if child.status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                self.jobs.cancel(child.id)
        return self.summary(batch_id)

    def retry_failed(self, batch_id: str) -> dict[str, Any]:
        for child in self.children(batch_id):
            if child.status is JobStatus.FAILED and child.attempt < child.max_attempts:
                self.jobs.retry(child.id)
                self.enqueue(child)
        return self.summary(batch_id)
