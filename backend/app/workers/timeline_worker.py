from __future__ import annotations

import hashlib
import json
import math
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

    def _validate_media_assets(self, job: GenerationJob, asset_ids: list[str], allowed_types: set[AssetType]) -> str | None:
        for asset_id in asset_ids:
            asset = self.assets.get(asset_id)
            if asset is None:
                return f"TIMELINE_ASSET_NOT_FOUND:{asset_id}"
            if asset.project_id != job.project_id:
                return f"TIMELINE_ASSET_PROJECT_MISMATCH:{asset_id}"
            if asset.status is not AssetStatus.READY:
                return f"TIMELINE_ASSET_NOT_READY:{asset_id}"
            if asset.type not in allowed_types:
                return f"TIMELINE_ASSET_TYPE_INVALID:{asset_id}:{asset.type.value}"
            if asset.provenance.license_status in {LicenseStatus.BLOCKED, LicenseStatus.RESTRICTED}:
                return f"TIMELINE_ASSET_LICENSE_BLOCKED:{asset_id}"
        return None

    @staticmethod
    def _duration_us(value: object, default: int = 1_000_000) -> int | None:
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number) or number <= 0:
            return None
        duration = int(number)
        return duration if duration > 0 else None

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")

        language_render = bool(job.input.parameters.get("languageRender"))
        if language_render:
            video_ids = [str(x) for x in job.input.parameters.get("videoAssetIds", []) if str(x)]
            audio_ids = [str(x) for x in job.input.parameters.get("audioAssetIds", []) if str(x)]
            subtitle_id = job.input.parameters.get("subtitleAssetId")
            if not video_ids:
                return JobExecutionResult(False, error_code="LANGUAGE_TIMELINE_NO_VIDEO", error_message="A language render requires a video asset")
            if (error := self._validate_media_assets(job, video_ids, {AssetType.VIDEO, AssetType.IMAGE})) is not None:
                return JobExecutionResult(False, error_code="TIMELINE_SOURCE_INVALID", error_message=error)
            if (error := self._validate_media_assets(job, audio_ids, {AssetType.AUDIO})) is not None:
                return JobExecutionResult(False, error_code="TIMELINE_SOURCE_INVALID", error_message=error)
            if subtitle_id:
                subtitle = str(subtitle_id)
                if (error := self._validate_media_assets(job, [subtitle], {AssetType.SUBTITLE})) is not None:
                    return JobExecutionResult(False, error_code="TIMELINE_SOURCE_INVALID", error_message=error)
            asset_ids = [*video_ids, *audio_ids] + ([str(subtitle_id)] if subtitle_id else [])
        else:
            video_ids = [str(x) for x in job.input.parameters.get("videoAssetIds", []) if str(x)]
            audio_ids = [str(x) for x in job.input.parameters.get("audioAssetIds", []) if str(x)]
            if not video_ids:
                refs = [str(x) for x in job.input.reference_asset_ids if str(x)]
                video_ids = [asset_id for asset_id in refs if (asset := self.assets.get(asset_id)) is not None and asset.type in {AssetType.VIDEO, AssetType.IMAGE}]
            if not video_ids:
                return JobExecutionResult(False, error_code="TIMELINE_NO_VIDEO", error_message="No playable video assets")
            if (error := self._validate_media_assets(job, video_ids, {AssetType.VIDEO, AssetType.IMAGE})) is not None:
                return JobExecutionResult(False, error_code="TIMELINE_SOURCE_INVALID", error_message=error)
            if (error := self._validate_media_assets(job, audio_ids, {AssetType.AUDIO})) is not None:
                return JobExecutionResult(False, error_code="TIMELINE_SOURCE_INVALID", error_message=error)
            asset_ids = [*video_ids, *audio_ids]

        if not asset_ids:
            return JobExecutionResult(False, error_code="TIMELINE_NO_ASSETS", error_message="No source assets")

        duration_us = self._duration_us(job.input.parameters.get("durationUs", 1_000_000))
        if duration_us is None:
            return JobExecutionResult(False, error_code="TIMELINE_DURATION_INVALID", error_message="durationUs must be finite and positive")

        timeline = Timeline(id=f"timeline:{job.id}", project_id=job.project_id, duration_us=duration_us)
        video_track = TimelineTrack(id=f"video:{job.id}", type=TrackType.VIDEO)
        video_duration = max(duration_us // len(video_ids), 1)
        for index, asset_id in enumerate(video_ids):
            start = index * video_duration
            clip_duration = duration_us - start if index == len(video_ids) - 1 else video_duration
            video_track.clips.append(TimelineClip(id=f"clip:{job.id}:v:{index}", asset_id=asset_id, start_us=start, duration_us=clip_duration, z_index=index))
        timeline.tracks.append(video_track)

        if audio_ids:
            audio_track_type = TrackType.DIALOGUE if language_render else TrackType.AUDIO
            audio_track = TimelineTrack(id=f"audio:{job.id}", type=audio_track_type)
            for index, asset_id in enumerate(audio_ids):
                audio_track.clips.append(TimelineClip(id=f"clip:{job.id}:a:{index}", asset_id=asset_id, start_us=0, duration_us=duration_us, z_index=index))
            timeline.tracks.append(audio_track)

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
            provenance=build_provenance(job, source_asset_ids=asset_ids, metadata={"timelineId": timeline.id, "languageRender": language_render}, license_status=LicenseStatus.VERIFIED, provider="internal", model="timeline-worker"),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"durationUs": timeline.duration_us, "clipCount": sum(len(t.clips) for t in timeline.tracks), "languageRender": language_render}, f"timeline-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
