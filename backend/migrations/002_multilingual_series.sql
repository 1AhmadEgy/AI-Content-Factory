-- AI Content Factory multilingual/country extension.
-- Safe to apply after 001_initial.sql.

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS country_id text,
  ADD COLUMN IF NOT EXISTS library_id text,
  ADD COLUMN IF NOT EXISTS source_language text,
  ADD COLUMN IF NOT EXISTS target_languages jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS dialect text,
  ADD COLUMN IF NOT EXISTS translation_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS glossary jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_projects_country_library ON projects(country_id, library_id);

CREATE TABLE IF NOT EXISTS translations (
  id text PRIMARY KEY,
  source_language text NOT NULL,
  target_language text NOT NULL,
  source_text text NOT NULL,
  translated_text text NOT NULL,
  content_type text NOT NULL,
  source_id text,
  source_version integer NOT NULL DEFAULT 1 CHECK(source_version > 0),
  provider text NOT NULL,
  model text,
  glossary_version integer NOT NULL DEFAULT 1 CHECK(glossary_version > 0),
  version integer NOT NULL DEFAULT 1 CHECK(version > 0),
  manual boolean NOT NULL DEFAULT false,
  source_fingerprint text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_translations_fingerprint_version
  ON translations(source_fingerprint, version);
CREATE INDEX IF NOT EXISTS idx_translations_source_target
  ON translations(source_id, target_language, version, created_at);
CREATE INDEX IF NOT EXISTS idx_translations_fingerprint
  ON translations(source_fingerprint);
CREATE INDEX IF NOT EXISTS idx_translations_current
  ON translations(source_fingerprint, manual DESC, version DESC, created_at DESC);

ALTER TABLE translations ENABLE ROW LEVEL SECURITY;
-- Translation rows are immutable history. If project-scoped ownership is introduced later,
-- add project_id and a matching RLS policy without changing the translation payload.
