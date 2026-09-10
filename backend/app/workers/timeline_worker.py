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

        duration_us = max(int(job.input.parameters.get("durationUs", 1_000_000)), 1)
        language_render = bool(job.input.parameters.get("languageRender"))
        if language_render:
            video_ids = [str(x) for x in job.input.parameters.get("videoAssetIds", [])]
            audio_ids = [str(x) for x in job.input.parameters.get("audioAssetIds", [])]
            subtitle_id = job.input.parameters.get("subtitleAssetId")
            selected = [*video_ids, *audio_ids]
            if subtitle_id:
                selected.append(str(subtitle_id))
            if not video_ids:
                return JobExecutionResult(False, error_code="LANGUAGE_TIMELINE_NO_VIDEO", error_message="A language render requires a video asset")
            missing = [asset_id for asset_id in selected if self.assets.get(asset_id) is None]
            if missing:
                return JobExecutionResult(False, error_code="TIMELINE_ASSET_NOT_FOUND", error_message=missing[0])
            asset_ids = selected

        timeline = Timeline(id=f"timeline:{job.id}", project_id=job.project_id, duration_us=duration_us)
        if language_render:
            video_ids = [str(x) for x in job.input.parameters.get("videoAssetIds", [])]
            audio_ids = [str(x) for x in job.input.parameters.get("audioAssetIds", [])]
            video_track = TimelineTrack(id=f"video:{job.id}", type=TrackType.VIDEO)
            video_duration = max(duration_us // len(video_ids), 1)
            for index, asset_id in enumerate(video_ids):
                start = index * video_duration
                video_track.clips.append(TimelineClip(id=f"clip:{job.id}:v:{index}", asset_id=asset_id, start_us=start, duration_us=video_duration if index < len(video_ids) - 1 else duration_us - start, z_index=index))
            timeline.tracks.append(video_track)
            if audio_ids:
                audio_track = TimelineTrack(id=f"audio:{job.id}", type=TrackType.DIALOGUE)
                for index, asset_id in enumerate(audio_ids):
                    audio_track.clips.append(TimelineClip(id=f"clip:{job.id}:a:{index}", asset_id=asset_id, start_us=0, duration_us=duration_us, z_index=index))
                timeline.tracks.append(audio_track)
        else:
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
            "languageRender": language_render,
            "language": job.input.parameters.get("language"),
            "locale": job.input.parameters.get("locale"),
            "subtitleAssetId": job.input.parameters.get("subtitleAssetId"),
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
            provenance=build_provenance(job, source_asset_ids=asset_ids, metadata={"timelineId": timeline.id, "languageRender": language_render}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"durationUs": timeline.duration_us, "clipCount": sum(len(t.clips) for t in timeline.tracks), "languageRender": language_render}, f"timeline-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
