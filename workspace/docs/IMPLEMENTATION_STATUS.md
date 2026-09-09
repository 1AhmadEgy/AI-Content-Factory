# Implementation Status

## Phase A: Baseline (v0.1)
- [x] 01 Build Health
- [x] 02 Package Cleanup
- [x] 03 Architecture
- [x] 04 Domain Models
- [x] 05 Room
- [x] 06 Repository
- [x] 07 Job Engine
- [x] 08 Mock Worker Contract + Deterministic Fixture Worker
- [x] 09 SQLite-backed Queue + Leasing

## Phase B: Production Core (v0.2)
- [~] 10 Asset System (domain + content-addressed local storage + SQLite metadata)
- [ ] 11 QC
- [ ] 12 Timeline
- [ ] 13 Renderer
- [x] 14 Backend Foundation (FastAPI + /api/v1 + SQLite persistence)
- [~] 15 Orchestrator (job state service + queue/worker contracts)

## Phase C: AI Story Factory (v0.3)
- [ ] 16 Story Agent
- [ ] 17 Character Bible
- [ ] 18 World Memory
- [ ] 19 Scene Planner
- [ ] 20 Shot Planner

## Phase D: Local AI (v0.4 - v1.0)
- [ ] 21 Local LLM
- [ ] 22 Image Worker
- [ ] 23 Video Worker
- [ ] 24 TTS
- [ ] 25 LipSync
- [ ] 26 Music/SFX
- [ ] 27 Full Pipeline
- [ ] 28 Batch Factory
- [ ] 29 Continuity
- [ ] 30 Analytics
- [ ] 31 Learning
- [ ] 32 Model Router
- [ ] 33 License Guard
- [ ] 34 Plugin System
- [ ] 35 Optional Cloud
- [ ] 36 v1.0

## Current engineering slice
- Persistent SQLite repository adapters are in place for projects, episodes, scenes, shots, and jobs.
- Jobs are exposed through `/api/v1/jobs` and projects through `/api/v1/projects`.
- Queue leasing is persisted in SQLite with priority ordering, heartbeats, acknowledgement, and expired-lease recovery.
- Asset metadata and content-addressed local storage are implemented.
- A deterministic mock worker creates real checksum-verifiable fixture assets with provenance.
- Backend tests and GitHub Actions CI have been added; CI execution is authoritative for pass/fail status.
