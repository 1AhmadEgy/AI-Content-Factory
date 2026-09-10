-- Runtime hardening for persisted provider attempts and idempotent scheduling.
-- Safe to apply after 001_initial.sql.
CREATE INDEX IF NOT EXISTS idx_provider_runs_job_created ON provider_runs(job_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_provider_runs_status_created ON provider_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_idempotency_operation ON idempotency_keys(operation, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_job ON assets(job_id, created_at DESC);

-- Keep schedule claiming deterministic when several workers wake together.
CREATE INDEX IF NOT EXISTS idx_schedules_claim ON schedules(enabled, next_run_at, id);
