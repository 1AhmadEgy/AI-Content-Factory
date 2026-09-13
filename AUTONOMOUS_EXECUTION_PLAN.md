# Autonomous Execution Plan

## Objective

Bring AI Content Factory to a production-grade state by continuously auditing, implementing, testing, and validating the repository without pausing for routine confirmation. Human input is required only for external credentials, irreversible production publication, or decisions that cannot be safely inferred from repository contracts.

## Execution order

1. **Repository integrity**
   - Inspect architecture, contracts, dependencies, generated files, configuration, and CI/CD.
   - Remove fake, simulated, placeholder, or silently-failing production paths.
   - Preserve public contracts unless a compatibility-safe migration is required.

2. **Backend correctness**
   - Enforce durable state transitions and idempotency.
   - Harden queue claiming, leases, heartbeats, expiry recovery, retries, cancellation, and concurrency.
   - Validate provider routing, capability matching, cache identity, circuit breakers, and provider-run audit records.
   - Ensure generated assets are content-addressed, integrity-checked, provenance-aware, and safely downloadable.

3. **API and security**
   - Enforce authentication when configured and never leak internal exception details.
   - Validate paths, hashes, URLs, request parameters, and persisted metadata.
   - Verify pagination, readiness, request IDs, and consistent error envelopes.
   - Keep cleartext transport disabled for production Android/backend connections.

4. **Real providers**
   - Keep production execution connected only to configured real provider adapters.
   - Fail explicitly when required credentials/model IDs are missing.
   - Do not manufacture fake provider output to make tests or production appear successful.

5. **Android release quality**
   - Validate Gradle configuration, dependency resolution, manifest/network security, release configuration, min/target SDK, versioning, shrinking, and test coverage.
   - Produce signed APK/AAB artifacts only through CI-controlled release paths.

6. **Google Play release gate**
   - Require the production upload keystore secrets for Play release builds.
   - Build and verify the release AAB and its signature.
   - Validate package/version metadata and artifact presence.
   - Never confuse the developer upload key with Google Play App Signing.
   - Do not publish to Play automatically unless Play Console publishing credentials and an explicit publishing workflow are configured.

7. **Verification**
   - Add regression tests for every material fix.
   - Run repository CI and inspect failed jobs/logs rather than assuming success.
   - Re-run only failed jobs when appropriate.
   - Keep the hardening PR in Draft until all applicable checks are verified.

8. **Continuous hardening loop**
   - After each verified batch, re-audit the changed surfaces and their callers.
   - Fix newly exposed compatibility or security issues.
   - Update documentation/contracts when behavior changes.
   - Repeat until remaining work is blocked only by external secrets, provider availability, or an explicit human production decision.

## Safety gates

The autonomous process may freely make reversible repository changes, add tests, update documentation, and improve CI. It must stop before:

- publishing a production release to Google Play;
- rotating or deleting production credentials;
- changing externally managed infrastructure with destructive impact;
- making a product decision where multiple incompatible interpretations are equally valid.

Those gates are deliberately narrow; routine implementation and verification should not wait for confirmation.
