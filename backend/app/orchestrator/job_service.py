from uuid import uuid4
from datetime import datetime, timezone
import sqlite3

from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from ..domain.repositories import JobRepository
from .job_state import transition


class JobService:
    def __init__(self, repository: JobRepository): self.repository=repository

    def create(self, *, project_id: str, job_type: JobType, target_type: str, target_id: str | None = None, parent_job_id: str | None = None, input: JobInput | None = None, priority: int = 100, max_attempts: int = 3, provider: str | None = None, model: str | None = None) -> GenerationJob:
        if max_attempts<1: raise ValueError("max_attempts must be >= 1")
        job=GenerationJob(id=str(uuid4()),project_id=project_id,type=job_type,target_type=target_type,target_id=target_id,parent_job_id=parent_job_id,input=input or JobInput(),priority=priority,max_attempts=max_attempts,provider=provider,model=model)
        transition(job,JobStatus.QUEUED);return self.repository.create(job)

    def create_with_idempotency(self, *, key: str, operation: str, fingerprint: str, project_id: str, job_type: JobType, target_type: str, target_id: str | None = None, parent_job_id: str | None = None, input: JobInput | None = None, priority: int = 100, max_attempts: int = 3, provider: str | None = None, model: str | None = None) -> tuple[GenerationJob | None, str | None]:
        """Atomically create a job and its idempotency record.

        Returns (job, existing_resource_id). The second value is populated when
        the key already exists. This method intentionally uses the SQLite
        repository's transaction boundary when available; other repositories
        fall back to the normal create path.
        """
        if not hasattr(self.repository, "store"):
            return self.create(project_id=project_id, job_type=job_type, target_type=target_type, target_id=target_id, parent_job_id=parent_job_id, input=input, priority=priority, max_attempts=max_attempts, provider=provider, model=model), None

        store = self.repository.store
        if max_attempts < 1: raise ValueError("max_attempts must be >= 1")
        job = GenerationJob(id=str(uuid4()), project_id=project_id, type=job_type, target_type=target_type, target_id=target_id, parent_job_id=parent_job_id, input=input or JobInput(), priority=priority, max_attempts=max_attempts, provider=provider, model=model)
        transition(job, JobStatus.QUEUED)
        now = datetime.now(timezone.utc).isoformat()
        input_json = __import__("json").dumps({"parameters": job.input.parameters, "referenceAssetIds": job.input.reference_asset_ids, "constraints": job.input.constraints, "seed": job.input.seed, "deterministic": job.input.deterministic}, separators=(",", ":"), ensure_ascii=False)
        with store._lock:
            store.connection.execute("BEGIN IMMEDIATE")
            try:
                existing = store.connection.execute("SELECT request_fingerprint, resource_id FROM idempotency_keys WHERE key=? AND operation=?", (key, operation)).fetchone()
                if existing is not None:
                    store.connection.commit()
                    return None, existing["resource_id"] if existing["request_fingerprint"] == fingerprint else "__IDEMPOTENCY_CONFLICT__"
                store.connection.execute("INSERT INTO jobs(id,parent_job_id,project_id,type,target_type,target_id,priority,status,progress,attempt,max_attempts,provider,model,input_json,output_json,error_code,error_message,created_at,started_at,completed_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (job.id, job.parent_job_id, job.project_id, job.type.value, job.target_type, job.target_id, job.priority, job.status.value, job.progress, job.attempt, job.max_attempts, job.provider, job.model, input_json, None, None, None, job.created_at.isoformat(), None, None, job.updated_at.isoformat()))
                store.connection.execute("INSERT INTO idempotency_keys(key,operation,request_fingerprint,resource_id,created_at) VALUES(?,?,?,?,?)", (key, operation, fingerprint, job.id, now))
                store.connection.commit()
                return job, None
            except sqlite3.IntegrityError:
                store.connection.rollback()
                existing = store.connection.execute("SELECT request_fingerprint, resource_id FROM idempotency_keys WHERE key=? AND operation=?", (key, operation)).fetchone()
                if existing is None:
                    raise
                return None, existing["resource_id"] if existing["request_fingerprint"] == fingerprint else "__IDEMPOTENCY_CONFLICT__"

    def cancel(self,job_id:str)->GenerationJob:
        job=self._get(job_id)
        if job.status in {JobStatus.COMPLETED,JobStatus.FAILED,JobStatus.CANCELLED}:return job
        transition(job,JobStatus.CANCELLED);job.error_code="CANCELLED_BY_USER";job.error_message="Job cancelled by user";return self.repository.update(job)

    def pause(self,job_id:str)->GenerationJob:
        job=self._get(job_id)
        if job.status not in {JobStatus.QUEUED,JobStatus.RUNNING}:raise ValueError("JOB_NOT_PAUSABLE")
        transition(job,JobStatus.PAUSED);return self.repository.update(job)

    def resume(self,job_id:str)->GenerationJob:
        job=self._get(job_id)
        if job.status not in {JobStatus.PAUSED,JobStatus.RETRYING}:raise ValueError("JOB_NOT_RESUMABLE")
        transition(job,JobStatus.QUEUED);return self.repository.update(job)

    def retry(self,job_id:str)->GenerationJob:
        job=self._get(job_id)
        if job.status not in {JobStatus.FAILED,JobStatus.RETRYING}:raise ValueError("JOB_NOT_RETRYABLE")
        if job.attempt>=job.max_attempts:raise ValueError("MAX_ATTEMPTS_REACHED")
        if job.status is JobStatus.FAILED:transition(job,JobStatus.RETRYING)
        transition(job,JobStatus.QUEUED);job.error_code=None;job.error_message=None;job.completed_at=None;job.updated_at=datetime.now(timezone.utc)
        return self.repository.update(job)

    def _get(self,job_id:str)->GenerationJob:
        job=self.repository.get(job_id)
        if job is None:raise KeyError("JOB_NOT_FOUND")
        return job
