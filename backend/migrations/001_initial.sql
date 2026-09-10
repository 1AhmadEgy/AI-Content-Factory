-- AI Content Factory PostgreSQL baseline
-- Apply with a migration runner in order; timestamps are UTC.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
  slug text UNIQUE, description text, status text NOT NULL DEFAULT 'DRAFT',
  settings jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(), archived_at timestamptz
);
CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), parent_job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  project_id uuid NOT NULL REFERENCES projects(id), type text NOT NULL, target_type text NOT NULL,
  target_id text, priority integer NOT NULL DEFAULT 50, status text NOT NULL DEFAULT 'PENDING',
  progress double precision NOT NULL DEFAULT 0 CHECK(progress>=0 AND progress<=1), attempt integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3 CHECK(max_attempts>0), provider text, model text,
  input jsonb NOT NULL DEFAULT '{}'::jsonb, output jsonb, error_code text, error_message text,
  created_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz, completed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_project_status_priority ON jobs(project_id,status,priority,created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status,priority,created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_parent ON jobs(parent_job_id);

CREATE TABLE IF NOT EXISTS job_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES projects(id), event_type text NOT NULL, status text NOT NULL,
  progress double precision NOT NULL DEFAULT 0, payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_job_events_job_created ON job_events(job_id,created_at,id);

CREATE TABLE IF NOT EXISTS schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
  operation text NOT NULL, payload jsonb NOT NULL DEFAULT '{}'::jsonb, run_at timestamptz NOT NULL,
  cron text, interval_seconds integer CHECK(interval_seconds IS NULL OR interval_seconds>0),
  timezone_name text NOT NULL DEFAULT 'UTC', enabled boolean NOT NULL DEFAULT true,
  last_run_at timestamptz, next_run_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((cron IS NULL) OR (interval_seconds IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(enabled,next_run_at);

CREATE TABLE IF NOT EXISTS assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
  type text NOT NULL, path text NOT NULL, mime text, size_bytes bigint, sha256 text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb, provider text, model text, prompt text,
  negative_prompt text, seed bigint, job_id uuid REFERENCES jobs(id), created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id,sha256)
);
CREATE INDEX IF NOT EXISTS idx_assets_project_type ON assets(project_id,type,created_at);

CREATE TABLE IF NOT EXISTS job_dependencies (
  job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  depends_on_job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(job_id,depends_on_job_id),
  CHECK(job_id<>depends_on_job_id)
);

CREATE TABLE IF NOT EXISTS provider_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_id uuid NOT NULL REFERENCES jobs(id), provider text NOT NULL,
  model text, request_metadata jsonb NOT NULL DEFAULT '{}'::jsonb, response_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
  duration_ms bigint, error_code text, created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  key text PRIMARY KEY, operation text NOT NULL, request_fingerprint text NOT NULL,
  resource_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);

-- Project isolation foundation. Enable RLS when application DB roles are provisioned.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_events ENABLE ROW LEVEL SECURITY;

-- Application deployments should create a scoped role and set app.project_id per transaction,
-- then install policies such as: USING (project_id = current_setting('app.project_id')::uuid).
