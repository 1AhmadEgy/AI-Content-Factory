# Uploaded Snapshot Merge

The uploaded `AI-Content-Factory-fixed.zip` was reviewed against the repository `main` snapshot. The uploaded snapshot is treated as a source snapshot, not as a destructive replacement: repository history and existing files are preserved, and only verified uploaded changes are merged.

## Source
- `AI-Content-Factory-fixed.zip`
- Reviewed: 2026-09-12

## Merge policy
- Preserve existing repository history.
- Do not commit Python cache files, `.pytest_cache`, build outputs, or generated artifacts from the ZIP.
- Preserve secrets and environment files as non-secret templates only.
- Keep the repository's existing architecture and contracts authoritative.

## Verified merge
- `backend/tests/test_content_pipeline.py` was updated from the uploaded snapshot to restore the compatible `Service.create(...)` test contract.
