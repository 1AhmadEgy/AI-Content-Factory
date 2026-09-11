# Contract Migration Gate — Job Lifecycle

**Status:** Required before changing runtime JobStatus values
**Current runtime:** `PENDING → QUEUED → RUNNING → COMPLETED` with legacy `RETRYING`, `PAUSED`, and `BLOCKED`
**Target contract:** `PENDING → QUEUED → LEASED → RUNNING → QC_PENDING → SUCCEEDED | FAILED | CANCELLED`

## Why this gate exists

The repository already has queue, lease, retry, completion-gate, API, and worker code that depends on the current lifecycle. Changing the enum alone would create partial migration failures across SQLite persistence, API serialization, retry/resume operations, tests, and documentation.

The migration therefore must be atomic at the contract boundary rather than a single-file refactor.

## Required migration sequence

1. Add versioned lifecycle vocabulary to the shared contract.
2. Add compatibility parsing for persisted legacy states.
3. Introduce `LEASED` as the persisted state created by an atomic queue claim.
4. Move attempt increment to the `LEASED → RUNNING` transition so a claim is not counted as execution.
5. Persist `QC_PENDING` before final acceptance.
6. Replace `COMPLETED` with `SUCCEEDED` only after output validation and QC acceptance.
7. Define retry semantics independently from lifecycle state (retry scheduling is metadata/control flow, not a success state).
8. Migrate API event names and client parsing together.
9. Add database migration tests for every legacy state and transition.
10. Run the Golden E2E path before merging the migration.

## Hard failure conditions

- A worker can produce `SUCCEEDED` without a valid Asset and required QC.
- A queue claim can execute without a persisted lease.
- An attempt counter increments twice for one execution.
- A legacy persisted status becomes unreadable.
- Android treats an unknown/new status as success.
- Retry or cancellation bypasses the state machine.

## Acceptance tests

At minimum, the migration must cover:

- valid and invalid state transitions;
- atomic claim and lease ownership;
- lease expiry and recovery;
- exactly-once attempt increment per execution;
- QC rejection cannot produce `SUCCEEDED`;
- successful output cannot bypass `QC_PENDING`;
- retry budget exhaustion produces `FAILED`;
- cancellation is terminal and distinct from failure;
- API serialization round-trip for every public status;
- legacy status migration/compatibility fixtures.

No runtime lifecycle replacement should be merged until these checks are green.
