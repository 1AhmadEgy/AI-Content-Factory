# Automation Gates

Production completion is evidence-based. CI success is required for each relevant change; missing credentials or production account secrets are explicit owner-controlled gates and must never be replaced with mocks.

## Required gates
- Backend syntax, lint and tests
- Asset generation and brand validation
- Android Gradle validation, unit tests and lint
- Debug APK, release APK and AAB builds
- APK/AAB structural validation and release signature verification
- Provider configuration/error-path tests
- Queue durability, leases, retries, idempotency and cancellation tests
- Asset path/content-addressing security tests
- Full end-to-end verification

## Safety
- Never commit API keys, keystores, passwords or production credentials.
- Never treat a simulated provider result as a successful production integration.
- Production signing and Play credentials remain owner-controlled.
