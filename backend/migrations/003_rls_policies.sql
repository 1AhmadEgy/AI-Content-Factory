-- Transaction/session setup expected before queries:
--   SET LOCAL app.project_id = '<project uuid>';
-- The policies intentionally fail closed when app.project_id is absent or invalid.

CREATE POLICY projects_project_scope ON projects
  USING (id = NULLIF(current_setting('app.project_id', true), '')::uuid)
  WITH CHECK (id = NULLIF(current_setting('app.project_id', true), '')::uuid);
CREATE POLICY jobs_project_scope ON jobs
  USING (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid)
  WITH CHECK (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid);
CREATE POLICY assets_project_scope ON assets
  USING (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid)
  WITH CHECK (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid);
CREATE POLICY schedules_project_scope ON schedules
  USING (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid)
  WITH CHECK (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid);
CREATE POLICY job_events_project_scope ON job_events
  USING (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid)
  WITH CHECK (project_id = NULLIF(current_setting('app.project_id', true), '')::uuid);

-- A privileged migration role may own the tables. The application role should not bypass RLS.
