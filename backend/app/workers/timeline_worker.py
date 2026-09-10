from __future__ import annotations

import hashlib
import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class TimelineWorker(Worker):
    """Build a validated, deterministic timeline manifest from selected assets."""

    worker_type = "timeline"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage = storage
        self.assets = assets
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        asset_ids = list(job.input.reference_asset_ids)
        if not asset_ids:
            return JobExecutionResult(False, error_code="TIMELINE_NO_ASSETS", error_message="No source assets")
        missing = [asset_id for asset_id in asset_ids if self.assets.get(asset_id) is None]
        if missing:
            return JobExecutionResult(False, error_code="TIMELINE_ASSET_NOT_FOUND", error_message=missing[0])

        duration_us = int(job.input.parameters.get("durationUs", 1_000_000))
        timeline = Timeline(id=f"timeline:{job.id}", project_id=job.project_id, duration_us=max(duration_us, 1))
        track = TimelineTrack(id=f"video:{job.id}", type=TrackType.VIDEO)
        clip_duration = max(duration_us // len(asset_ids), 1)
        for index, asset_id in enumerate(asset_ids):
            track.clips.append(TimelineClip(
                id=f"clip:{job.id}:{index}", asset_id=asset_id,
                start_us=index * clip_duration,
                duration_us=clip_duration if index < len(asset_ids) - 1 else duration_us - index * clip_duration,
                z_index=index,
            ))
        timeline.tracks.append(track)
        errors = timeline.validate()
        if errors:
            return JobExecutionResult(False, error_code="TIMELINE_INVALID", error_message=errors[0])

        manifest = {
            "timelineId": timeline.id,
            "projectId": timeline.project_id,
            "durationUs": timeline.duration_us,
            "timebase": timeline.timebase,
            "tracks": [{
                "id": t.id, "type": t.type.value,
                "clips": [{"id": c.id, "assetId": c.asset_id, "startUs": c.start_us, "durationUs": c.duration_us, "sourceStartUs": c.source_start_us, "zIndex": c.z_index} for c in t.clips],
            } for t in timeline.tracks],
        }
        payload = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"timeline:{job.id}:{digest}"))
        asset = Asset(
            id=asset_id, project_id=job.project_id, type=AssetType.DOCUMENT,
            path=path, mime_type="application/json; charset=utf-8", size_bytes=size,
            sha256=digest, status=AssetStatus.READY,
            provenance=build_provenance(job, source_asset_ids=asset_ids, metadata={"timelineId": timeline.id}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"durationUs": timeline.duration_us, "clipCount": len(asset_ids)}, f"timeline-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
