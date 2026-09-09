from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from ..domain.jobs import GenerationJob, JobStatus
from ..orchestrator.queue import JobLease, JobQueue
from .sqlite import SQLiteJobRepository, SQLiteStore, _dt, _job_from_row, _parse_dt


class SQLiteJobQueue(JobQueue):
    """Persistent single-database queue with atomic leases and recovery."""

    def __init__(self, store: SQLiteStore, jobs: SQLiteJobRepository, lease_seconds: int = 300) -> None:
        self.store = store
        self.jobs = jobs
        self.lease_seconds = lease_seconds
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                """CREATE TABLE IF NOT EXISTS job_leases (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                    worker_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_leases_expiry ON job_leases(expires_at)"
            )

    def enqueue(self, job: GenerationJob) -> None:
        if job.status is not JobStatus.QUEUED:
            raise ValueError("Only QUEUED jobs may be enqueued")
        self.jobs.update(job)

    def claim_next(self, worker_id: str) -> tuple[GenerationJob, JobLease] | None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.lease_seconds)
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                row = self.store.connection.execute(
                    """SELECT j.* FROM jobs j
                    LEFT JOIN job_leases l ON l.job_id = j.id
                    WHERE j.status = 'QUEUED' AND l.job_id IS NULL
                    ORDER BY j.priority DESC, j.created_at ASC
                    LIMIT 1"""
                ).fetchone()
                if row is None:
                    self.store.connection.commit()
                    return None
                lease = JobLease(
                    job_id=row["id"],
                    worker_id=worker_id,
                    lease_id=str(uuid.uuid4()),
                    expires_at=expires.isoformat(),
                )
                self.store.connection.execute(
                    "INSERT INTO job_leases(job_id,worker_id,lease_id,expires_at,created_at) VALUES(?,?,?,?,?)",
                    (lease.job_id, lease.worker_id, lease.lease_id, lease.expires_at, now.isoformat()),
                )
                self.store.connection.execute(
                    "UPDATE jobs SET status='RUNNING', attempt=attempt+1, started_at=?, updated_at=? WHERE id=?",
                    (now.isoformat(), now.isoformat(), lease.job_id),
                )
                self.store.connection.commit()
            except Exception:
                self.store.connection.rollback()
                raise
        refreshed = self.jobs.get(lease.job_id)
        if refreshed is None:
            raise RuntimeError(f"Claimed job disappeared: {lease.job_id}")
        return refreshed, lease

    def heartbeat(self, lease: JobLease) -> None:
        expires = datetime.now(timezone.utc) + timedelta(seconds=self.lease_seconds)
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
                (expires.isoformat(), lease.job_id, lease.lease_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("JOB_LEASE_NOT_FOUND")

    def acknowledge(self, lease: JobLease, status: JobStatus) -> None:
        if status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.RETRYING}:
            raise ValueError("Acknowledge requires a terminal or retry state")
        now = datetime.now(timezone.utc)
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                lease_row = self.store.connection.execute(
                    "SELECT job_id FROM job_leases WHERE job_id=? AND lease_id=?",
                    (lease.job_id, lease.lease_id),
                ).fetchone()
                if lease_row is None:
                    raise KeyError("JOB_LEASE_NOT_FOUND")
                self.store.connection.execute(
                    "UPDATE jobs SET status=?, completed_at=?, updated_at=? WHERE id=?",
                    (status.value, now.isoformat() if status is not JobStatus.RETRYING else None, now.isoformat(), lease.job_id),
                )
                self.store.connection.execute("DELETE FROM job_leases WHERE job_id=?", (lease.job_id,))
                self.store.connection.commit()
            except Exception:
                self.store.connection.rollback()
                raise

    def release_expired(self) -> int:
        now = datetime.now(timezone.utc)
        with self.store._lock:
            self.store.connection.execute("BEGIN IMMEDIATE")
            try:
                rows = self.store.connection.execute(
                    "SELECT job_id FROM job_leases WHERE expires_at <= ?", (now.isoformat(),)
                ).fetchall()
                for row in rows:
                    self.store.connection.execute(
                        "UPDATE jobs SET status='RETRYING', updated_at=?, error_code='LEASE_EXPIRED', error_message='Worker lease expired' WHERE id=? AND status='RUNNING'",
                        (now.isoformat(), row["job_id"]),
                    )
                    self.store.connection.execute("DELETE FROM job_leases WHERE job_id=?", (row["job_id"],))
                self.store.connection.commit()
                return len(rows)
            except Exception:
                self.store.connection.rollback()
                raise
