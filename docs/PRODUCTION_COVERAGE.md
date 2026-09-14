# Production Coverage

This is the evidence checklist for production hardening on the development branch.

- Backend syntax/lint/tests: required and continuously checked by CI.
- Canonical brand assets: generated and validated by CI.
- Android: Gradle validation, unit tests, lint, APK/AAB builds and artifact/signature checks are defined in CI.
- Real provider integration: requires owner-controlled credentials; missing credentials must produce configuration errors, never fake results.
- Production signing/Play publication: requires owner-controlled secrets and account decisions.
- Final completion requires observable green CI plus artifact inspection and end-to-end verification.
