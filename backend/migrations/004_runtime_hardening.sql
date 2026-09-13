-- Runtime hardening migration after 003_rls_policies.sql.
-- The application currently initializes SQLite schema directly in
-- backend/app/infrastructure/sqlite.py; this file is retained as the
-- canonical forward migration for deployments that apply SQL migrations.

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_operation
    ON idempotency_keys(operation, created_at);
