-- Runtime hardening for persisted provider attempts, scheduling and idempotent execution.
-- Safe to apply after 003_rls_policies.sql.

-- Persist retry availability so workers cannot immediately reclaim a failed job.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS idx_jobs_runnable ON jobs(status, available_at, priority DESC, created_at);

CREATE INDEX IF NOT EXISTS idx_provider_runs_job_created ON provider_runs(job_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_provider_runs_status_created ON provider_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_idempotency_operation ON idempotency_keys(operation, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_job ON assets(job_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_dependencies_depends_on ON job_dependencies(depends_on_job_id, job_id);

-- Keep schedule claiming deterministic when several workers wake together.
CREATE INDEX IF NOT EXISTS idx_schedules_claim ON schedules(enabled, next_run_at, id);
