# Queue & Scheduler Specification

**Version:** 1.0  
**Status:** Normative Engineering Specification  
**Scope:** AI-Content-Factory

## 1. Purpose

The Queue and Scheduler subsystem controls when Generation Jobs execute, where they execute, how resources are reserved, how dependencies are respected, and how failures/retries/cancellation are handled.

It MUST remain independent from any single AI provider, model, GPU vendor, runtime, or deployment platform.

## 2. Architectural Position

```text
API / Workflow
      ↓
Generation Job
      ↓
Dependency Resolver
      ↓
Queue
      ↓
Scheduler
      ↓
Model Router
      ↓
Resource Manager
      ↓
Worker Lease
      ↓
Worker / Provider / Model
      ↓
Artifact + QC
      ↓
Job Completion Event
```

The Queue stores work. The Scheduler decides eligibility and allocation. Workers execute work. These responsibilities MUST NOT be collapsed into one component.

## 3. Core Principles

1. Persistent jobs are authoritative.
2. In-memory queues are acceleration layers, never the production source of truth.
3. Jobs MUST be safely recoverable after process restart.
4. Dependencies MUST be explicit.
5. Scheduling MUST be resource-aware.
6. A job MUST have one authoritative execution lease at a time.
7. Duplicate execution MUST be prevented or made idempotent.
8. Retry policy MUST distinguish transient from permanent failures.
9. Cancellation MUST be explicit and observable.
10. Priority MUST NOT permanently starve lower-priority jobs.
11. A worker MUST NOT execute a job it cannot satisfy.
12. Completed jobs require valid outputs and required QC gates.

## 4. Job State Machine

```text
PENDING
  ↓
QUEUED
  ↓
RUNNING
  ├──→ COMPLETED
  ├──→ FAILED
  ├──→ RETRYING → QUEUED
  ├──→ PAUSED → QUEUED
  └──→ CANCELLED
```

Allowed transitions MUST be validated centrally.

Invalid transitions MUST return a domain error rather than silently changing state.

## 5. Queue Record

Minimum persistent queue metadata:

```text
jobId
projectId
priority
status
enqueuedAt
availableAt
scheduledAt
attempt
maxAttempts
leaseId
leaseExpiresAt
workerId
resourceReservationId
lastErrorCode
lastErrorMessage
createdAt
updatedAt
```

The implementation may store these fields directly on the Job or in dedicated queue tables, provided the semantics remain equivalent.

## 6. Priority

Recommended priority levels:

```text
CRITICAL
HIGH
NORMAL
LOW
BACKGROUND
```

Priority MUST be configurable and MUST NOT be the only scheduling factor.

Aging MUST be supported so old low-priority jobs eventually receive service.

## 7. Fairness / Anti-Starvation

The scheduler SHOULD combine:

```text
priority
age
project fairness
resource fit
workflow criticality
estimated execution time
```

A project generating thousands of jobs MUST NOT automatically monopolize every worker.

Optional fair-share scheduling may allocate per-project concurrency or weighted quotas.

## 8. Dependency Graph

Jobs MAY depend on other jobs.

```text
Story Job
   ↓
Scene Job
   ↓
Shot Job
   ├── Image Job
   ├── Video Job
   └── TTS Job
          ↓
      LipSync Job
          ↓
       QC Job
          ↓
     Timeline Job
          ↓
      Render Job
```

A dependent job becomes runnable only when all required dependencies reach an acceptable terminal state.

## 9. Dependency Policies

Each dependency SHOULD declare:

```text
required
allowedStatuses
artifactRequirements
failurePolicy
```

Examples:

```text
REQUIRED + COMPLETED only
REQUIRED + COMPLETED with QC PASS
OPTIONAL + COMPLETED/FAILED
```

Optional dependencies MUST never accidentally block a workflow.

## 10. Cycle Prevention

The system MUST reject dependency graphs containing cycles.

Cycle validation SHOULD happen at job creation and before scheduling.

A job MUST NOT be accepted into a runnable queue if its dependency graph is invalid.

## 11. Runnable Job Definition

A job is runnable only when all required conditions are satisfied:

```text
status == QUEUED
AND availableAt <= now
AND required dependencies satisfied
AND project is active
AND policy permits execution
AND a compatible model/provider exists
AND resources can be reserved
AND no conflicting lease exists
```

## 12. Scheduler Loop

Conceptual algorithm:

```text
repeat:
    recoverExpiredLeases()
    refreshWorkerHealth()
    candidates = loadRunnableJobs()
    candidates = applyDependencies(candidates)
    candidates = applyPolicy(candidates)
    candidates = resolveModels(candidates)
    candidates = filterByResources(candidates)
    ordered = rank(candidates)
    for job in ordered:
        if resourcesAvailable(job):
            reservation = reserve(job)
            lease = acquireLease(job, reservation)
            dispatch(job, lease)
```

The scheduler MUST use atomic/concurrency-safe operations around reservation and lease acquisition.

## 13. Queue Selection Strategy

A recommended score is:

```text
score = priorityWeight
      + agingWeight
      + workflowCriticality
      + fairnessAdjustment
      + resourceFit
      - estimatedCost
      - estimatedRuntimePenalty
```

The exact formula is implementation-specific. Hard constraints MUST be evaluated before scoring.

## 14. Resource Manager Boundary

The Scheduler asks whether a job can run; the Resource Manager owns actual resource accounting.

Resources include:

```text
CPU
RAM
GPU
VRAM
GPU slots
storage
network bandwidth where relevant
worker concurrency
provider quotas
```

A job MUST NOT assume resources based solely on static model metadata.

## 15. Resource Reservation

Recommended flow:

```text
candidate
→ estimate requirements
→ reserve resources atomically
→ acquire job lease
→ dispatch
→ release on terminal state
```

Reservation MUST have an owner and lifecycle.

If dispatch fails, reservation MUST be released or reconciled safely.

## 16. GPU Scheduling

GPU-aware scheduling SHOULD consider:

```text
gpuId
gpuVendor
gpuArchitecture
VRAM total
VRAM free
compute capability
active jobs
exclusive/shared mode
model residency
```

A model that requires 16 GB VRAM MUST NOT be dispatched to a worker with insufficient available VRAM merely because the physical GPU has 16 GB total.

## 17. Model Residency

Workers MAY keep models loaded in memory.

The scheduler SHOULD consider model residency to reduce load/unload overhead while still respecting fairness and resource limits.

Residency is an optimization, never a correctness requirement.

## 18. Worker Registration

A worker MUST register:

```text
workerId
status
capabilities
supportedModelIds/runtimeTypes
CPU/RAM/GPU resources
concurrency limits
version
heartbeatAt
metadata
```

Workers MUST report health periodically.

## 19. Worker States

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
OFFLINE
```

`DRAINING` means the worker accepts no new jobs but may finish existing leases.

## 20. Heartbeats

Workers SHOULD send heartbeats containing:

```text
workerId
heartbeatAt
activeLeaseIds
resourceSnapshot
health
```

A missed heartbeat beyond the configured timeout causes the worker to be considered unhealthy/offline.

## 21. Leases

A lease prevents two schedulers/workers from believing they own the same job.

Minimum lease fields:

```text
leaseId
jobId
workerId
acquiredAt
expiresAt
renewedAt
status
```

Lease acquisition MUST be atomic.

Workers SHOULD renew leases periodically for long-running jobs.

## 22. Lease Expiration

When a lease expires:

1. Mark the worker suspect/unhealthy if appropriate.
2. Verify whether execution actually completed.
3. Reconcile artifacts/provider state.
4. Avoid duplicate completion.
5. Requeue or fail according to retry policy.

A lease expiration MUST NOT blindly start a duplicate expensive generation if provider-side execution may still be running and cannot be queried safely.

## 23. Idempotency

Every externally initiated generation/render/publish operation SHOULD have an idempotency key.

Recommended identity:

```text
projectId + idempotencyKey
```

Repeated requests with the same key MUST return the existing logical operation rather than create uncontrolled duplicate jobs.

## 24. Job Deduplication

Optional content-based deduplication MAY use a normalized fingerprint:

```text
jobType
inputHash
referenceAssetHashes
modelId/version
parameters
seed
determinism settings
```

Deduplication MUST never incorrectly reuse an asset when required inputs differ.

The system SHOULD distinguish:

```text
same request
same job
same artifact
```

These are not always equivalent.

## 25. Dispatch Protocol

Conceptually:

```text
Scheduler → Worker: Execute(job, lease)
Worker → Scheduler: Accepted
Worker → Events: Progress
Worker → Scheduler: Completed/Failed
```

A worker MUST acknowledge ownership only after a valid lease exists.

## 26. Progress

Progress MUST be normalized to:

```text
0..100
```

Workers MAY report richer phase metadata:

```text
phase
phaseProgress
message
eta
```

Progress MUST NOT be interpreted as proof of successful completion.

## 27. Completion

A worker may report execution complete, but the orchestrator remains responsible for validating:

1. expected artifacts exist.
2. artifacts are readable.
3. checksums/metadata can be recorded.
4. required QC passes.
5. database state can be committed consistently.

Only then may the logical Job become `COMPLETED`.

## 28. Retry Classification

Retryable examples:

```text
PROVIDER_UNAVAILABLE
RESOURCE_UNAVAILABLE
GPU_UNAVAILABLE
TIMEOUT
transient network failure
worker crash
```

Normally non-retryable:

```text
VALIDATION_ERROR
MODEL_LICENSE_BLOCKED
unsupported capability
invalid workflow
corrupt input
permission failure
```

The error code contract is defined by `CONTRACTS_SPECIFICATION.md`.

## 29. Retry Policy

Recommended fields:

```text
maxAttempts
initialDelay
maxDelay
backoffMultiplier
jitter
retryableCodes
```

Use bounded exponential backoff with jitter for transient infrastructure failures.

A retry MUST increment the attempt number and emit a retry event.

## 30. Fallback

Fallback to another model/provider is allowed only when the Model Router policy permits it.

```text
Primary fails
→ classify failure
→ evaluate fallback policy
→ route compatible candidate
→ create/continue execution according to idempotency rules
```

Fallback decisions MUST be recorded in provenance and telemetry.

## 31. Cancellation

Cancellation states:

```text
REQUESTED
ACKNOWLEDGED
CANCELLED
CANCEL_FAILED
```

A cancellation request MUST be persisted.

Workers SHOULD terminate execution when safely possible.

If the provider cannot cancel an already submitted remote job, the system MUST record that fact and prevent unsafe duplicate execution.

## 32. Pause / Resume

Jobs MAY be paused when the underlying operation supports safe pausing.

If true pause is impossible, the implementation MUST emulate pause at queue boundaries rather than claiming active computation was paused.

Resume MUST revalidate dependencies, model availability, license policy, and resources.

## 33. Project Isolation

Scheduler policies SHOULD support per-project:

```text
maxConcurrentJobs
maxGPUJobs
maxQueueDepth
priorityQuota
storageQuota
```

Project isolation MUST prevent one project from exhausting shared infrastructure.

## 34. Backpressure

The system MUST apply backpressure when:

- queue depth is excessive.
- storage is near capacity.
- GPU resources are exhausted.
- provider quotas are exhausted.
- workers are unhealthy.

Possible actions:

```text
slow intake
reject new work
queue work
reduce concurrency
prefer lighter models
```

Backpressure MUST be observable.

## 35. Batch Jobs

Batch workflows SHOULD be represented as a parent job plus child jobs.

```text
BatchJob
 ├── ChildJob 1
 ├── ChildJob 2
 └── ChildJob N
```

Parent completion depends on its declared aggregation policy:

```text
ALL_REQUIRED
ANY_SUCCESS
BEST_EFFORT
QUORUM
```

## 36. Workflow Criticality

Jobs MAY declare criticality:

```text
BLOCKING
IMPORTANT
OPTIONAL
BACKGROUND
```

A render job may be blocked by a required QC job while thumbnail generation may remain optional.

Criticality affects scheduling and dependency handling but does not override hard resource/license constraints.

## 37. Crash Recovery

On scheduler startup:

```text
load non-terminal jobs
find expired leases
inspect worker registrations
reconcile provider runs where possible
release stale reservations
requeue recoverable jobs
mark unrecoverable jobs failed
resume scheduling
```

Recovery MUST be deterministic and safe to execute repeatedly.

## 38. Scheduler High Availability

If multiple scheduler instances run concurrently, they MUST coordinate using database locks, leases, or an equivalent distributed coordination mechanism.

Two schedulers MUST NOT dispatch the same job simultaneously.

## 39. Persistence

Recommended entities:

```text
jobs
job_dependencies
job_attempts
job_leases
job_events
resource_reservations
worker_registrations
provider_runs
```

Exact table design must remain consistent with `DATABASE_SCHEMA_SPECIFICATION.md`.

## 40. Transaction Boundaries

Job enqueue SHOULD atomically persist:

```text
job
+ dependencies
+ idempotency record
+ initial event
```

Dispatch SHOULD atomically establish the lease and reservation before worker ownership is acknowledged.

Completion SHOULD atomically persist job state and relevant artifact/provider/QC references where feasible.

## 41. Event Ordering

Events MUST contain:

```text
eventId
jobId
type
timestamp
sequence/version
payload
```

Consumers MUST tolerate duplicate and out-of-order events according to `API_SPECIFICATION.md`.

## 42. Queue Events

Minimum events:

```text
JOB_QUEUED
JOB_STARTED
JOB_PROGRESS
JOB_RETRYING
JOB_PAUSED
JOB_COMPLETED
JOB_FAILED
JOB_CANCELLED
JOB_LEASE_EXPIRED
JOB_FALLBACK_SELECTED
RESOURCE_RESERVED
RESOURCE_RELEASED
```

## 43. Observability

Track:

```text
queueDepth
queueWaitTime
schedulerCycleTime
dispatchRate
executionTime
leaseExpirationRate
retryRate
fallbackRate
workerUtilization
GPUUtilization
VRAMUtilization
failureRate
cancellationRate
```

Logs MUST include correlation identifiers such as `requestId`, `jobId`, `leaseId`, and `workerId`.

## 44. Security

Workers MUST authenticate to the scheduler/backend.

A worker MUST NOT be able to execute arbitrary jobs outside its authorized project/resource scope.

Secrets MUST never be embedded in jobs or queue records.

## 45. Replit / Local / GPU Deployment

The scheduler MAY run with the backend on Replit or another lightweight environment.

Heavy inference SHOULD remain on dedicated GPU/local workers.

The scheduler communicates through a stable worker protocol and does not assume that worker processes share the backend filesystem.

Artifacts SHOULD use durable shared storage or explicit upload/download protocols.

## 46. Mock Mode

Mock workers MUST allow the complete queue lifecycle to run without GPU hardware or external providers.

CI MUST be able to exercise:

```text
enqueue
→ dependency resolution
→ scheduling
→ lease
→ execution
→ progress
→ artifact
→ QC
→ completion
```

Mock execution MUST be deterministic.

## 47. Testing Strategy

### Unit Tests

- priority calculation
- aging
- dependency resolution
- cycle detection
- retry classification
- backoff
- idempotency
- cancellation state transitions
- resource fit
- lease expiration

### Integration Tests

- database queue persistence
- concurrent schedulers
- worker registration
- reservation lifecycle
- dispatch protocol
- crash recovery

### Contract Tests

- worker contract
- provider contract
- event contract
- job lifecycle contract

### E2E

Run the Golden Pipeline using mock workers.

## 48. Failure Scenarios That MUST Be Tested

1. Scheduler crashes before dispatch.
2. Scheduler crashes after lease creation.
3. Worker crashes during execution.
4. Worker disappears after completion but before acknowledgement.
5. Provider times out but continues running remotely.
6. Two schedulers select the same job.
7. Resource reservation succeeds but dispatch fails.
8. Dependency completes while scheduler is offline.
9. Duplicate API request arrives.
10. Cancellation arrives during execution.
11. Model becomes unavailable after queueing.
12. GPU becomes unavailable after reservation.
13. Disk becomes full during artifact creation.
14. QC blocks completion.
15. Fallback model is incompatible.

## 49. Non-Negotiable Rules

1. Never use an in-memory queue as the production source of truth.
2. Never dispatch without a valid lease.
3. Never ignore job dependencies.
4. Never oversubscribe reserved resources intentionally.
5. Never retry permanent failures.
6. Never hide fallback decisions.
7. Never mark a job completed merely because a worker returned success.
8. Never lose job attempt history.
9. Never allow duplicate scheduler dispatch through a race condition.
10. Never bypass Model Router/Resource Manager for AI jobs.
11. Never expose secrets through queue payloads or logs.
12. Never let a single project monopolize infrastructure without an explicit policy.
13. Never claim pause/cancel capability that the underlying runtime does not support.
14. Never destroy provenance during retry or fallback.
15. Never make CI depend on a live external AI provider.

## 50. Implementation Order

### P0 — Persistent Job Core
- Job state machine.
- Queue persistence.
- Dependencies.
- Events.
- Idempotency.

### P1 — Scheduler
- Runnable selection.
- Priority/aging.
- Lease acquisition.
- Dispatch.
- Worker heartbeat.

### P2 — Resource Scheduling
- Resource Manager integration.
- GPU/VRAM awareness.
- Reservations.
- Concurrency limits.
- Project quotas.

### P3 — Reliability
- Retry/backoff.
- Cancellation.
- Crash recovery.
- Lease reconciliation.
- Provider fallback.

### P4 — Scale and Quality
- Fair-share scheduling.
- Multi-scheduler coordination.
- Advanced model residency.
- Metrics.
- Load tests.

## 51. Definition of Done

The Queue and Scheduler subsystem is production-ready only when:

- Jobs persist across restarts.
- Dependencies are enforced.
- Cycles are rejected.
- Idempotency works.
- Leases prevent duplicate ownership.
- Resources are reserved/released safely.
- GPU/VRAM constraints are enforced.
- Priority and aging work.
- Project fairness/backpressure work.
- Retry classification is correct.
- Cancellation semantics are honest.
- Crash recovery is tested.
- Multiple schedulers are race-safe if deployed.
- Events are durable and observable.
- Mock mode completes the Golden Pipeline.
- Contract/integration/E2E tests pass.
- Documentation matches implementation.

## 52. Relationship to Other Specifications

This specification must remain consistent with:

- `PROJECT_RULES.md`
- `DEVELOPER_IMPLEMENTATION_GUIDE.md`
- `CONTRACTS_SPECIFICATION.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`
- `WORKER_PROVIDER_ARCHITECTURE.md`
- `AI_MODEL_REGISTRY_SPECIFICATION.md`

Any conflict MUST be resolved through an explicit versioned specification change.

---

**Final rule:** A job is not merely a task waiting in a list. It is a persistent, dependency-aware, resource-constrained, lease-protected execution unit whose lifecycle must remain correct through retries, failures, cancellation, worker loss, and restart.