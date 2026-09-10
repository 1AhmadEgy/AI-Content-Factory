from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable

from ..domain.job_events import JobEvent
from ..domain.jobs import GenerationJob, JobOutput, JobStatus
from ..domain.repositories import JobRepository
from ..workers.registry import WorkerRegistry
from .completion_gate import CompletionGate
from .heartbeat import LeaseHeartbeat
from .job_state import transition
from .queue import JobLease, JobQueue, Worker, WorkerContext

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    job: GenerationJob
    status: JobStatus
    retried: bool = False

class JobExecutor:
    """Runs a leased GenerationJob and durably records its lifecycle."""
    def __init__(self, jobs: JobRepository, queue: JobQueue, workers: WorkerRegistry, events: Callable[[JobEvent], None] | None = None, on_completed: Callable[[GenerationJob], None] | None = None, heartbeat_interval_seconds: float | None = None, completion_gate: CompletionGate | None = None) -> None:
        self.jobs = jobs
        self.queue = queue
        self.workers = workers
        self.emit = events or (lambda _event: None)
        self.on_completed = on_completed or (lambda _job: None)
        self.completion_gate = completion_gate
        configured_interval = heartbeat_interval_seconds
        if configured_interval is None:
            configured_interval = float(os.getenv("AICF_LEASE_HEARTBEAT_SECONDS", "5.0"))
        if configured_interval <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        self.heartbeat_interval_seconds = configured_interval

    def execute_claimed(self, job: GenerationJob, lease: JobLease, *, worker_id: str | None = None) -> ExecutionResult:
        worker_id = worker_id or lease.worker_id
        worker: Worker = self.workers.get(worker_id)
        if not worker.health_check():
            return self._fail(job, lease, "WORKER_UNHEALTHY", "Worker health check failed", retryable=True)
        if job.status is not JobStatus.RUNNING:
            raise ValueError(f"Job must be RUNNING before execution: {job.status}")
        self._event(job, "JOB_STARTED", {"workerId": worker_id, "attempt": job.attempt})
        self._set_progress(job, "worker_execution", 0.05, lease=lease)
        heartbeat = LeaseHeartbeat(self.queue, lease, interval_seconds=self.heartbeat_interval_seconds)
        heartbeat.start()
        try:
            result = worker.execute(job, WorkerContext(worker_id=worker_id, lease_id=lease.lease_id, metadata={"attempt": job.attempt}, progress_callback=lambda progress, stage: self._set_progress(job, stage, progress, lease=lease)))
        except Exception as exc:
            return self._fail(job, lease, "WORKER_EXCEPTION", str(exc), retryable=True)
        finally:
            heartbeat.stop()
        if not self.queue.is_lease_active(lease):
            raise RuntimeError("JOB_LEASE_LOST")
        if not result.success:
            return self._fail(job, lease, result.error_code or "WORKER_FAILED", result.error_message or "Worker execution failed", result.retryable)
        if not result.asset_ids:
            return self._fail(job, lease, "MISSING_OUTPUT_ASSET", "Successful worker execution returned no assets", retryable=False)
        job.output = JobOutput(asset_ids=list(result.asset_ids), metrics=dict(result.metrics), provider_run_id=result.provider_run_id)
        job.error_code = None
        job.error_message = None
        if self.completion_gate is None:
            raise RuntimeError("COMPLETION_GATE_NOT_CONFIGURED")
        gate = self.completion_gate.check(job)
        if not gate.allowed:
            job.error_code = gate.code or "COMPLETION_GATE_BLOCKED"
            job.error_message = gate.message or "Completion gate rejected the output"
            self._require_persisted(job, lease)
            transition(job, JobStatus.BLOCKED)
            self.queue.acknowledge(lease, JobStatus.BLOCKED)
            self._event(job, "JOB_BLOCKED", {"errorCode": job.error_code, "qcCount": len(gate.qc_results)})
            return ExecutionResult(job, JobStatus.BLOCKED)
        self._set_progress(job, "completed", 1.0, persist=False, lease=lease)
        self._require_persisted(job, lease)
        transition(job, JobStatus.COMPLETED)
        self.queue.acknowledge(lease, JobStatus.COMPLETED)
        self._event(job, "JOB_COMPLETED", {"assetIds": result.asset_ids, "providerRunId": result.provider_run_id, "qcCount": len(gate.qc_results), "progress": 1.0})
        self._notify_completed(job)
        return ExecutionResult(job, JobStatus.COMPLETED)

    def cancel_claimed(self, job: GenerationJob, lease: JobLease, worker_id: str | None = None) -> ExecutionResult:
        if not self.queue.is_lease_active(lease):
            raise RuntimeError("JOB_LEASE_LOST")
        worker = self.workers.get(worker_id or lease.worker_id)
        worker.cancel(job.id)
        job.error_code = "CANCELLED"
        job.error_message = "Cancellation requested"
        self._require_persisted(job, lease)
        transition(job, JobStatus.CANCELLED)
        self.queue.acknowledge(lease, JobStatus.CANCELLED)
        self._event(job, "JOB_CANCELLED", {})
        return ExecutionResult(job, JobStatus.CANCELLED)

    def _set_progress(self, job: GenerationJob, stage: str, progress: float, *, persist: bool = True, lease: JobLease | None = None) -> None:
        if lease is not None and not self.queue.is_lease_active(lease):
            return
        job.progress = max(0.0, min(1.0, float(progress)))
        if persist:
            if lease is not None:
                if not self._persist_claimed(job, lease):
                    return
            else:
                self.jobs.update(job)
        self._event(job, "JOB_PROGRESS", {"stage": stage, "progress": job.progress})

    def _fail(self, job: GenerationJob, lease: JobLease, code: str, message: str, retryable: bool) -> ExecutionResult:
        if not self.queue.is_lease_active(lease):
            raise RuntimeError("JOB_LEASE_LOST")
        job.error_code = code
        job.error_message = message
        if retryable and job.attempt < job.max_attempts:
            self._require_persisted(job, lease)
            transition(job, JobStatus.RETRYING)
            self.queue.acknowledge(lease, JobStatus.RETRYING)
            transition(job, JobStatus.QUEUED)
            self._event(job, "JOB_RETRY_SCHEDULED", {"errorCode": code, "attempt": job.attempt, "maxAttempts": job.max_attempts})
            return ExecutionResult(job, JobStatus.QUEUED, retried=True)
        self._require_persisted(job, lease)
        transition(job, JobStatus.FAILED)
        self.queue.acknowledge(lease, JobStatus.FAILED)
        self._event(job, "JOB_FAILED", {"errorCode": code, "retryable": retryable, "attempt": job.attempt})
        return ExecutionResult(job, JobStatus.FAILED)

    def _persist_claimed(self, job: GenerationJob, lease: JobLease) -> bool:
        if not self.queue.is_lease_active(lease):
            return False
        update_if_current = getattr(self.jobs, "update_if_current", None)
        if update_if_current is not None:
            return bool(update_if_current(job, JobStatus.RUNNING, job.attempt))
        self.jobs.update(job)
        return True

    def _require_persisted(self, job: GenerationJob, lease: JobLease) -> None:
        if not self._persist_claimed(job, lease):
            raise RuntimeError("JOB_LEASE_LOST")

    def _notify_completed(self, job: GenerationJob) -> None:
        try:
            self.on_completed(job)
        except Exception:
            logger.exception("Post-completion callback failed for job %s", job.id)

    def _event(self, job: GenerationJob, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.emit(JobEvent.create(job.id, job.project_id, event_type, job.status.value, job.progress, payload))
        except Exception:
            logger.exception("Job event emission failed for %s (%s)", job.id, event_type)
