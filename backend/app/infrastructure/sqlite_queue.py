from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from ..domain.jobs import GenerationJob, JobStatus
from ..orchestrator.queue import JobLease, JobQueue
from .sqlite import SQLiteJobRepository, SQLiteStore


class SQLiteJobQueue(JobQueue):
    """Persistent single-database queue with atomic leases, dependencies and retry scheduling."""

    def __init__(self, store: SQLiteStore, jobs: SQLiteJobRepository, lease_seconds: int = 300, retry_initial_delay_seconds: float = 2.0, retry_max_delay_seconds: float = 300.0, retry_backoff_multiplier: float = 2.0, retry_jitter_ratio: float = 0.20, random_source: object | None = None) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        if retry_initial_delay_seconds < 0:
            raise ValueError("retry_initial_delay_seconds must not be negative")
        if retry_max_delay_seconds < retry_initial_delay_seconds:
            raise ValueError("retry_max_delay_seconds must be >= retry_initial_delay_seconds")
        if retry_backoff_multiplier < 1.0:
            raise ValueError("retry_backoff_multiplier must be >= 1")
        if not 0.0 <= retry_jitter_ratio <= 1.0:
            raise ValueError("retry_jitter_ratio must be between 0 and 1")
        self.store = store
        self.jobs = jobs
        self.lease_seconds = lease_seconds
        self.retry_initial_delay_seconds = retry_initial_delay_seconds
        self.retry_max_delay_seconds = retry_max_delay_seconds
        self.retry_backoff_multiplier = retry_backoff_multiplier
        self.retry_jitter_ratio = retry_jitter_ratio
        self._random = random_source or random
        with self.store._lock, self.store.connection:
            self.store.connection.execute("""CREATE TABLE IF NOT EXISTS job_leases (
                job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                worker_id TEXT NOT NULL, lease_id TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL, created_at TEXT NOT NULL)""")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_job_leases_expiry ON job_leases(expires_at)")
            self.store.connection.execute("""CREATE TABLE IF NOT EXISTS job_retry_schedule (
                job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                available_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_job_retry_available ON job_retry_schedule(available_at, job_id)")
            self.store.connection.execute("""CREATE TABLE IF NOT EXISTS job_dependencies (
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                depends_on_job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY(job_id, depends_on_job_id), CHECK(job_id <> depends_on_job_id))""")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_job_dependencies_dependency ON job_dependencies(depends_on_job_id, job_id)")

    def enqueue(self, job: GenerationJob) -> None:
        if job.status is not JobStatus.QUEUED:
            raise ValueError("Only QUEUED jobs may be enqueued")
        current = self.jobs.get(job.id)
        if current is None:
            raise KeyError(f"Job not found: {job.id}")
        if current.status is not JobStatus.QUEUED:
            raise RuntimeError(f"Job is no longer QUEUED: {job.id}")

    def add_dependency(self, job_id: str, depends_on_job_id: str) -> None:
        if not job_id.strip() or not depends_on_job_id.strip():
            raise ValueError("job ids must not be empty")
        if job_id == depends_on_job_id:
            raise ValueError("A job cannot depend on itself")
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                rows = self.store.connection.execute("SELECT id, project_id FROM jobs WHERE id IN (?, ?)", (job_id, depends_on_job_id)).fetchall()
                if len(rows) != 2:
                    raise KeyError("Both jobs must exist before adding a dependency")
                if len({row["project_id"] for row in rows}) != 1:
                    raise ValueError("Cross-project job dependencies are not allowed")
                cycle = self.store.connection.execute("""WITH RECURSIVE reachable(job_id) AS (
                    SELECT depends_on_job_id FROM job_dependencies WHERE job_id = ?
                    UNION
                    SELECT d.depends_on_job_id FROM job_dependencies d JOIN reachable r ON d.job_id = r.job_id)
                    SELECT 1 FROM reachable WHERE job_id = ? LIMIT 1""", (depends_on_job_id, job_id)).fetchone()
                if cycle is not None:
                    raise ValueError("Dependency cycle detected")
                self.store.connection.execute("INSERT OR IGNORE INTO job_dependencies(job_id, depends_on_job_id, created_at) VALUES(?,?,?)", (job_id, depends_on_job_id, datetime.now(timezone.utc).isoformat()))
                self.store.connection.commit()
            except Exception:
                self.store.connection.rollback()
                raise

    def remove_dependency(self, job_id: str, depends_on_job_id: str) -> bool:
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute("DELETE FROM job_dependencies WHERE job_id=? AND depends_on_job_id=?", (job_id, depends_on_job_id))
            return cursor.rowcount == 1

    def dependencies(self, job_id: str) -> list[str]:
        with self.store._lock:
            rows = self.store.connection.execute("SELECT depends_on_job_id FROM job_dependencies WHERE job_id=? ORDER BY depends_on_job_id", (job_id,)).fetchall()
        return [row["depends_on_job_id"] for row in rows]

    def dependencies_satisfied(self, job_id: str) -> bool:
        with self.store._lock:
            row = self.store.connection.execute("""SELECT 1 FROM job_dependencies d
                LEFT JOIN jobs dependency ON dependency.id = d.depends_on_job_id
                WHERE d.job_id=? AND (dependency.id IS NULL OR dependency.status <> 'COMPLETED') LIMIT 1""", (job_id,)).fetchone()
        return row is None

    def block_jobs_with_failed_dependencies(self) -> int:
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute("""UPDATE jobs SET status='BLOCKED', completed_at=NULL, updated_at=?,
                error_code='DEPENDENCY_FAILED', error_message='A required dependency reached a non-success terminal state'
                WHERE status IN ('QUEUED','RETRYING') AND EXISTS (
                    SELECT 1 FROM job_dependencies d JOIN jobs dependency ON dependency.id=d.depends_on_job_id
                    WHERE d.job_id=jobs.id AND dependency.status IN ('FAILED','CANCELLED','BLOCKED'))""", (datetime.now(timezone.utc).isoformat(),))
            return cursor.rowcount

    def claim_next(self, worker_id: str) -> tuple[GenerationJob, JobLease] | None:
        return self._claim(worker_id, None)

    def claim(self, job_id: str, worker_id: str) -> tuple[GenerationJob, JobLease] | None:
        if not job_id.strip():
            raise ValueError("job_id must not be empty")
        return self._claim(worker_id, job_id)

    def _claim(self, worker_id: str, job_id: str | None) -> tuple[GenerationJob, JobLease] | None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.lease_seconds)
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                self.store.connection.execute("""UPDATE jobs SET status='BLOCKED', updated_at=?, error_code='DEPENDENCY_FAILED',
                    error_message='A required dependency reached a non-success terminal state'
                    WHERE status IN ('QUEUED','RETRYING') AND EXISTS (
                        SELECT 1 FROM job_dependencies d JOIN jobs dependency ON dependency.id=d.depends_on_job_id
                        WHERE d.job_id=jobs.id AND dependency.status IN ('FAILED','CANCELLED','BLOCKED'))""", (now.isoformat(),))
                eligibility = """j.status IN ('QUEUED','RETRYING') AND l.job_id IS NULL
                    AND (r.available_at IS NULL OR r.available_at <= ?)
                    AND NOT EXISTS (SELECT 1 FROM job_dependencies d
                        LEFT JOIN jobs dependency ON dependency.id=d.depends_on_job_id
                        WHERE d.job_id=j.id AND (dependency.id IS NULL OR dependency.status <> 'COMPLETED'))"""
                if job_id is None:
                    row = self.store.connection.execute(f"""SELECT j.* FROM jobs j
                        LEFT JOIN job_leases l ON l.job_id=j.id LEFT JOIN job_retry_schedule r ON r.job_id=j.id
                        WHERE {eligibility} ORDER BY j.priority DESC, j.created_at ASC LIMIT 1""", (now.isoformat(),)).fetchone()
                else:
                    row = self.store.connection.execute(f"""SELECT j.* FROM jobs j
                        LEFT JOIN job_leases l ON l.job_id=j.id LEFT JOIN job_retry_schedule r ON r.job_id=j.id
                        WHERE j.id=? AND {eligibility} LIMIT 1""", (job_id, now.isoformat())).fetchone()
                if row is None:
                    self.store.connection.commit()
                    return None
                lease = JobLease(job_id=row["id"], worker_id=worker_id, lease_id=str(uuid.uuid4()), expires_at=expires.isoformat())
                self.store.connection.execute("INSERT INTO job_leases(job_id,worker_id,lease_id,expires_at,created_at) VALUES(?,?,?,?,?)", (lease.job_id, lease.worker_id, lease.lease_id, lease.expires_at, now.isoformat()))
                cursor = self.store.connection.execute("""UPDATE jobs SET status='RUNNING', attempt=attempt+1,
                    started_at=?, completed_at=NULL, updated_at=? WHERE id=? AND status IN ('QUEUED','RETRYING')""", (now.isoformat(), now.isoformat(), lease.job_id))
                if cursor.rowcount != 1:
                    raise RuntimeError(f"Failed to transition claimed job: {lease.job_id}")
                self.store.connection.execute("DELETE FROM job_retry_schedule WHERE job_id=?", (lease.job_id,))
                self.store.connection.commit()
            except Exception:
                self.store.connection.rollback()
                raise
        refreshed = self.jobs.get(lease.job_id)
        if refreshed is None:
            raise RuntimeError(f"Claimed job disappeared: {lease.job_id}")
        return refreshed, lease

    def heartbeat(self, lease: JobLease) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.lease_seconds)
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute("UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=? AND expires_at > ?", (expires.isoformat(), lease.job_id, lease.lease_id, now.isoformat()))
            if cursor.rowcount != 1:
                raise KeyError("JOB_LEASE_NOT_FOUND")

    def is_lease_active(self, lease: JobLease) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.store._lock:
            row = self.store.connection.execute("SELECT 1 FROM job_leases WHERE job_id=? AND lease_id=? AND expires_at > ?", (lease.job_id, lease.lease_id, now)).fetchone()
        return row is not None

    def _retry_delay_seconds(self, attempt: int) -> float:
        retry_number = max(1, attempt)
        base = min(self.retry_max_delay_seconds, self.retry_initial_delay_seconds * (self.retry_backoff_multiplier ** (retry_number - 1)))
        jitter = base * self.retry_jitter_ratio
        return max(0.0, min(self.retry_max_delay_seconds, base + self._random.uniform(-jitter, jitter)))

    def _schedule_retry(self, job_id: str, attempt: int, now: datetime) -> None:
        delay = self._retry_delay_seconds(attempt)
        available_at = now + timedelta(seconds=delay)
        self.store.connection.execute("""INSERT INTO job_retry_schedule(job_id,available_at,updated_at) VALUES(?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET available_at=excluded.available_at, updated_at=excluded.updated_at""", (job_id, available_at.isoformat(), now.isoformat()))

    def acknowledge(self, lease: JobLease, status: JobStatus) -> None:
        if status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.RETRYING, JobStatus.BLOCKED}:
            raise ValueError("Acknowledge requires a terminal or retry state")
        now = datetime.now(timezone.utc)
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                lease_row = self.store.connection.execute("SELECT job_id FROM job_leases WHERE job_id=? AND lease_id=? AND expires_at > ?", (lease.job_id, lease.lease_id, now.isoformat())).fetchone()
                if lease_row is None:
                    raise KeyError("JOB_LEASE_NOT_FOUND")
                job_row = self.store.connection.execute("SELECT attempt FROM jobs WHERE id=? AND status='RUNNING'", (lease.job_id,)).fetchone()
                if job_row is None:
                    raise RuntimeError(f"Job is no longer RUNNING: {lease.job_id}")
                completed_at = now.isoformat() if status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED} else None
                persisted_status = JobStatus.QUEUED if status is JobStatus.RETRYING else status
                cursor = self.store.connection.execute("UPDATE jobs SET status=?, completed_at=?, updated_at=? WHERE id=? AND status='RUNNING'", (persisted_status.value, completed_at, now.isoformat(), lease.job_id))
                if cursor.rowcount != 1:
                    raise RuntimeError(f"Job is no longer RUNNING: {lease.job_id}")
                if status is JobStatus.RETRYING:
                    self._schedule_retry(lease.job_id, job_row["attempt"], now)
                else:
                    self.store.connection.execute("DELETE FROM job_retry_schedule WHERE job_id=?", (lease.job_id,))
                self.store.connection.execute("DELETE FROM job_leases WHERE job_id=? AND lease_id=?", (lease.job_id, lease.lease_id))
                self.store.connection.commit()
            except Exception:
                self.store.connection.rollback()
                raise

    def release_expired(self) -> int:
        now = datetime.now(timezone.utc)
        recovered = 0
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                rows = self.store.connection.execute("SELECT l.job_id, j.attempt, j.max_attempts FROM job_leases l JOIN jobs j ON j.id=l.job_id WHERE l.expires_at <= ? AND j.status='RUNNING'", (now.isoformat(),)).fetchall()
                for row in rows:
                    next_status = "RETRYING" if row["attempt"] < row["max_attempts"] else "FAILED"
                    cursor = self.store.connection.execute("""UPDATE jobs SET status=?, updated_at=?, completed_at=?,
                        error_code='LEASE_EXPIRED', error_message=? WHERE id=? AND status='RUNNING'""", (next_status, now.isoformat(), now.isoformat() if next_status == "FAILED" else None, "Worker lease expired; job scheduled for retry" if next_status == "RETRYING" else "Worker lease expired; retry budget exhausted", row["job_id"]))
                    if cursor.rowcount == 1:
                        if next_status == "RETRYING":
                            self._schedule_retry(row["job_id"], row["attempt"], now)
                        else:
                            self.store.connection.execute("DELETE FROM job_retry_schedule WHERE job_id=?", (row["job_id"],))
                        self.store.connection.execute("DELETE FROM job_leases WHERE job_id=?", (row["job_id"],))
                        recovered += 1
                self.store.connection.commit()
                return recovered
            except Exception:
                self.store.connection.rollback()
                raise
