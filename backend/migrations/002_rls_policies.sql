-- Transaction/session setup expected before queries:
--   SET LOCAL app.project_id = '<project uuid>';
--
-- Policies intentionally fail closed when app.project_id is absent, empty, or
-- malformed. We compare against project_id::text instead of casting the session
-- setting to uuid, so an attacker-controlled invalid value cannot raise a cast
-- exception and turn isolation into an application error.
--
-- Production deployments should use a dedicated application role that does
-- NOT own these tables and does NOT have BYPASSRLS. Migration/admin roles may
-- retain ownership/BYPASSRLS as required for schema management.

DROP POLICY IF EXISTS projects_project_scope ON projects;
CREATE POLICY projects_project_scope ON projects
  USING (id::text = NULLIF(current_setting('app.project_id', true), ''))
  WITH CHECK (id::text = NULLIF(current_setting('app.project_id', true), ''));

DROP POLICY IF EXISTS jobs_project_scope ON jobs;
CREATE POLICY jobs_project_scope ON jobs
  USING (project_id::text = NULLIF(current_setting('app.project_id', true), ''))
  WITH CHECK (project_id::text = NULLIF(current_setting('app.project_id', true), ''));

DROP POLICY IF EXISTS assets_project_scope ON assets;
CREATE POLICY assets_project_scope ON assets
  USING (project_id::text = NULLIF(current_setting('app.project_id', true), ''))
  WITH CHECK (project_id::text = NULLIF(current_setting('app.project_id', true), ''));

DROP POLICY IF EXISTS schedules_project_scope ON schedules;
CREATE POLICY schedules_project_scope ON schedules
  USING (project_id::text = NULLIF(current_setting('app.project_id', true), ''))
  WITH CHECK (project_id::text = NULLIF(current_setting('app.project_id', true), ''));

DROP POLICY IF EXISTS job_events_project_scope ON job_events;
CREATE POLICY job_events_project_scope ON job_events
  USING (project_id::text = NULLIF(current_setting('app.project_id', true), ''))
  WITH CHECK (project_id::text = NULLIF(current_setting('app.project_id', true), ''));

-- Keep RLS enabled explicitly in case this migration is re-applied to a
-- database where a previous maintenance operation disabled it.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_events ENABLE ROW LEVEL SECURITY;
