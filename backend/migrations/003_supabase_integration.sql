-- Supabase integration foundation for AI Content Factory
-- Requires Supabase Auth and PostgreSQL.
-- Runtime AI/API secrets stay in Edge Function secrets; this schema stores configuration only.

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS owner_user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projects_owner_user
  ON projects(owner_user_id);

CREATE TABLE IF NOT EXISTS project_members (
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'editor'
    CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_project_members_user
  ON project_members(user_id, project_id);

CREATE TABLE IF NOT EXISTS ai_provider_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  provider text NOT NULL,
  model text NOT NULL,
  capability text NOT NULL DEFAULT 'text',
  enabled boolean NOT NULL DEFAULT true,
  priority integer NOT NULL DEFAULT 100,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, provider, model, capability)
);

CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_route
  ON ai_provider_configs(project_id, capability, enabled, priority);

CREATE TABLE IF NOT EXISTS usage_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  provider text NOT NULL,
  model text,
  capability text NOT NULL,
  input_units bigint NOT NULL DEFAULT 0 CHECK (input_units >= 0),
  output_units bigint NOT NULL DEFAULT 0 CHECK (output_units >= 0),
  duration_ms bigint CHECK (duration_ms IS NULL OR duration_ms >= 0),
  estimated_cost numeric(18,8) CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_project_created
  ON usage_events(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_job
  ON usage_events(job_id, created_at DESC);

-- Bring existing job/provider/idempotency records under project-aware RLS.
ALTER TABLE job_dependencies
  ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(id) ON DELETE CASCADE;

ALTER TABLE provider_runs
  ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(id) ON DELETE CASCADE;

ALTER TABLE idempotency_keys
  ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_job_dependencies_project
  ON job_dependencies(project_id);

CREATE INDEX IF NOT EXISTS idx_provider_runs_project
  ON provider_runs(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_idempotency_project
  ON idempotency_keys(project_id, created_at DESC);

-- Backfill project ownership for existing relational records where it is unambiguous.
UPDATE job_dependencies jd
SET project_id = j.project_id
FROM jobs j
WHERE jd.project_id IS NULL
  AND j.id = jd.job_id;

UPDATE provider_runs pr
SET project_id = j.project_id
FROM jobs j
WHERE pr.project_id IS NULL
  AND j.id = pr.job_id;

UPDATE idempotency_keys ik
SET project_id = j.project_id
FROM jobs j
WHERE ik.project_id IS NULL
  AND j.id = ik.resource_id;

-- RLS for all Supabase-exposed project-scoped tables.
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

-- Existing policies are intentionally named explicitly so this migration is idempotent
-- when the database has already received the earlier project-scope policies.
DROP POLICY IF EXISTS projects_project_scope ON projects;
DROP POLICY IF EXISTS jobs_project_scope ON jobs;
DROP POLICY IF EXISTS assets_project_scope ON assets;
DROP POLICY IF EXISTS schedules_project_scope ON schedules;
DROP POLICY IF EXISTS job_events_project_scope ON job_events;

CREATE POLICY projects_member_select ON projects
  FOR SELECT TO authenticated
  USING (
    owner_user_id = (select auth.uid())
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = projects.id
        AND pm.user_id = (select auth.uid())
    )
  );

CREATE POLICY projects_owner_insert ON projects
  FOR INSERT TO authenticated
  WITH CHECK (owner_user_id = (select auth.uid()));

CREATE POLICY projects_member_update ON projects
  FOR UPDATE TO authenticated
  USING (
    owner_user_id = (select auth.uid())
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = projects.id
        AND pm.user_id = (select auth.uid())
        AND pm.role IN ('owner', 'admin', 'editor')
    )
  )
  WITH CHECK (
    owner_user_id = (select auth.uid())
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = projects.id
        AND pm.user_id = (select auth.uid())
        AND pm.role IN ('owner', 'admin', 'editor')
    )
  );

CREATE POLICY project_members_self_or_admin ON project_members
  FOR SELECT TO authenticated
  USING (
    user_id = (select auth.uid())
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = project_members.project_id
        AND pm.user_id = (select auth.uid())
        AND pm.role IN ('owner', 'admin')
    )
  );

CREATE POLICY project_members_admin_write ON project_members
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = project_members.project_id
        AND p.owner_user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = project_members.project_id
        AND pm.user_id = (select auth.uid())
        AND pm.role IN ('owner', 'admin')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = project_members.project_id
        AND p.owner_user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = project_members.project_id
        AND pm.user_id = (select auth.uid())
        AND pm.role IN ('owner', 'admin')
    )
  );

CREATE POLICY ai_provider_configs_member ON ai_provider_configs
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = ai_provider_configs.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = ai_provider_configs.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = ai_provider_configs.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = ai_provider_configs.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY usage_events_member_read ON usage_events
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = usage_events.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = usage_events.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY jobs_member_scope ON jobs
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = jobs.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = jobs.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = jobs.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = jobs.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY assets_member_scope ON assets
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = assets.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = assets.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = assets.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = assets.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY schedules_member_scope ON schedules
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = schedules.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = schedules.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = schedules.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = schedules.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY job_events_member_scope ON job_events
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = job_events.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = job_events.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY job_dependencies_member_scope ON job_dependencies
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = job_dependencies.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = job_dependencies.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = job_dependencies.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = job_dependencies.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY provider_runs_member_scope ON provider_runs
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = provider_runs.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = provider_runs.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

CREATE POLICY idempotency_member_scope ON idempotency_keys
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = idempotency_keys.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = idempotency_keys.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM project_members pm
      WHERE pm.project_id = idempotency_keys.project_id
        AND pm.user_id = (select auth.uid())
    )
    OR EXISTS (
      SELECT 1 FROM projects p
      WHERE p.id = idempotency_keys.project_id
        AND p.owner_user_id = (select auth.uid())
    )
  );

-- Service/backend workers can use the Supabase secret key and intentionally bypass RLS.
-- Never expose that key to Android/web clients.
