from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from ..domain.job_events import JobEvent
from ..domain.jobs import GenerationJob, JobOutput, JobStatus
from ..workers.registry import WorkerRegistry
from .completion_gate import CompletionGate
from .heartbeat import LeaseHeartbeat
from .job_state import transition
from .queue import JobLease, JobQueue, Worker, WorkerContext


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    job: GenerationJob
    status: JobStatus
    retried: bool = False


class JobExecutor:
    """Runs a leased GenerationJob and durably records its lifecycle."""

    def __init__(self, jobs, queue: JobQueue, workers: WorkerRegistry, events: Callable[[JobEvent], None] | None = None, on_completed: Callable[[GenerationJob], None] | None = None, heartbeat_interval_seconds: float | None = None, completion_gate: CompletionGate | None = None) -> None:
        self.jobs = jobs
        self.queue = queue
        self.workers = workers
        self.emit = events or (lambda _event: None)
        self.on_completed = on_completed or (lambda _job: None)
        self.completion_gate = completion_gate
        interval = heartbeat_interval_seconds if heartbeat_interval_seconds is not None else float(os.getenv("AICF_LEASE_HEARTBEAT_SECONDS", "5.0"))
        if interval <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        self.heartbeat_interval_seconds = interval

    def execute_claimed(self, job: GenerationJob, lease: JobLease, *, worker_id: str | None = None) -> ExecutionResult:
        worker_id = worker_id or lease.worker_id
        worker: Worker = self.workers.get(worker_id)
        if not worker.health_check():
            return self._fail(job, lease, "WORKER_UNHEALTHY", "Worker health check failed", True)
        if job.status is not JobStatus.RUNNING:
            raise ValueError(f"Job must be RUNNING before execution: {job.status}")

        self._event(job, "JOB_STARTED", {"workerId": worker_id, "attempt": job.attempt})
        # Do not manufacture a percentage while the worker is running. The
        # backend remains the lifecycle authority; a real worker can report
        # progress through a future progress callback without fake updates.
        heartbeat = LeaseHeartbeat(self.queue, lease, interval_seconds=self.heartbeat_interval_seconds)
        heartbeat.start()
        try:
            result = worker.execute(job, WorkerContext(worker_id=worker_id, lease_id=lease.lease_id, metadata={"attempt": job.attempt}))
        except Exception as exc:
            return self._fail(job, lease, "WORKER_EXCEPTION", str(exc), True)
        finally:
            heartbeat.stop()

        if not result.success:
            return self._fail(job, lease, result.error_code or "WORKER_FAILED", result.error_message or "Worker execution failed", result.retryable)
        if not result.asset_ids:
            return self._fail(job, lease, "MISSING_OUTPUT_ASSET", "Successful worker execution returned no assets", False)

        job.output = JobOutput(asset_ids=list(result.asset_ids), metrics=dict(result.metrics), provider_run_id=result.provider_run_id)
        job.error_code = None
        job.error_message = None
        if self.completion_gate is None:
            raise RuntimeError("COMPLETION_GATE_NOT_CONFIGURED")

        gate = self.completion_gate.check(job)
        if not gate.allowed:
            job.error_code = gate.code or "COMPLETION_GATE_BLOCKED"
            job.error_message = gate.message or "Completion gate rejected the output"
            transition(job, JobStatus.BLOCKED)
            self.jobs.update(job)
            self.queue.acknowledge(lease, JobStatus.BLOCKED)
            self._event(job, "JOB_BLOCKED", {"errorCode": job.error_code, "qcCount": len(gate.qc_results)})
            return ExecutionResult(job, JobStatus.BLOCKED)

        transition(job, JobStatus.COMPLETED)
        self.jobs.update(job)
        self.queue.acknowledge(lease, JobStatus.COMPLETED)
        self._event(job, "JOB_COMPLETED", {"assetIds": result.asset_ids, "providerRunId": result.provider_run_id, "qcCount": len(gate.qc_results)})
        self.on_completed(job)
        return ExecutionResult(job, JobStatus.COMPLETED)

    def cancel_claimed(self, job: GenerationJob, lease: JobLease, worker_id: str | None = None) -> ExecutionResult:
        worker = self.workers.get(worker_id or lease.worker_id)
        worker.cancel(job.id)
        transition(job, JobStatus.CANCELLED)
        job.error_code = "CANCELLED"
        job.error_message = "Cancellation requested"
        self.jobs.update(job)
        self.queue.acknowledge(lease, JobStatus.CANCELLED)
        self._event(job, "JOB_CANCELLED", {})
        return ExecutionResult(job, JobStatus.CANCELLED)

    def _fail(self, job: GenerationJob, lease: JobLease, code: str, message: str, retryable: bool) -> ExecutionResult:
        job.error_code = code
        job.error_message = message
        can_retry = retryable and job.attempt < job.max_attempts
        if can_retry:
            transition(job, JobStatus.RETRYING)
            self.jobs.update(job)
            self.queue.acknowledge(lease, JobStatus.RETRYING)
            transition(job, JobStatus.QUEUED)
            self.jobs.update(job)
            self._event(job, "JOB_RETRY_SCHEDULED", {"errorCode": code, "attempt": job.attempt, "maxAttempts": job.max_attempts})
            return ExecutionResult(job, JobStatus.QUEUED, retried=True)
        transition(job, JobStatus.FAILED)
        self.jobs.update(job)
        self.queue.acknowledge(lease, JobStatus.FAILED)
        self._event(job, "JOB_FAILED", {"errorCode": code, "retryable": retryable, "attempt": job.attempt})
        return ExecutionResult(job, JobStatus.FAILED)

    def _event(self, job: GenerationJob, event_type: str, payload: dict[str, object]) -> None:
        self.emit(JobEvent.create(job.id, job.project_id, event_type, job.status.value, job.progress, payload))
