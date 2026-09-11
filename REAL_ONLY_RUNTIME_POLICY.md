# Real-Only Runtime Policy

**Status:** Normative — applies to production/runtime behavior on `codex/advanced-repair-wave-1` and subsequent releases.

## Purpose

AI Content Factory must never report a successful production operation when the requested real output was not actually produced and validated.

## Prohibited production behavior

The runtime MUST NOT use:

- mock, fake, dummy, placeholder, simulated, or deterministic fixture providers as production providers;
- timer/sleep based progress or success simulation;
- fabricated media bytes, fake MP4/JPEG/audio/video outputs, or manifests presented as media;
- dry-run publishing that reports publication success;
- silent fallback from a missing/failed real provider to fabricated output;
- automatic substitution of an unconfigured provider/model without an explicit configured policy;
- QC that passes merely because an asset record exists.

## Required behavior

Every successful production stage MUST have an inspectable real output appropriate to its asset type.

At minimum, success gates MUST establish:

1. the output asset exists on storage;
2. the stored file is non-empty where applicable;
3. the recorded SHA-256 matches the actual stored bytes;
4. the asset belongs to the expected project and has an allowed type/status;
5. technical validation appropriate to the asset type has passed;
6. required QC has passed;
7. external publishing is reported successful only when the configured external service confirms publication with an external identifier.

If a real provider, executable, credential, endpoint, source asset, or required capability is unavailable, the stage MUST fail explicitly with a stable error code. It must never manufacture a success result.

## Determinism is not simulation

Deterministic algorithms are allowed for validation, scheduling, hashing, timeline construction, and other pure domain operations. The prohibition applies to deterministic **fixtures that pretend to be real provider/media output**.

## Documentation rule

Historical audit documents may mention removed mock/simulation behavior for traceability, but they must be clearly understood as historical. Normative implementation documents must not describe mock mode as a valid production execution path.

## Change gate

Any new worker/provider/publisher/renderer that can return `success=True` must include tests proving that success is impossible when the real output is missing, invalid, or unverified.
