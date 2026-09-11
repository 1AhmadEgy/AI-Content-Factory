from __future__ import annotations

import logging
import os
from dataclasses import replace
from pathlib import Path

from ..application.ai_scene_planner import AIScenePlanner
from ..application.ai_script_engine import AIScriptEngine
from ..application.ai_story_engine import AIStoryEngine
from ..domain.content import ContentBrief, StoryPlan
from ..domain.jobs import GenerationJob, JobStatus, JobType
from ..infrastructure.asset_repository import SQLiteAssetRepository
from ..infrastructure.character_repository import SQLiteCharacterRepository
from ..infrastructure.location_repository import SQLiteLocationRepository
from ..infrastructure.job_event_repository import SQLiteJobEventRepository
from ..infrastructure.provider_run_repository import SQLiteProviderRunRepository
from ..infrastructure.shot_composition_repository import SQLiteShotCompositionRepository
from ..infrastructure.sqlite import SQLiteRepositories
from ..infrastructure.sqlite_queue import SQLiteJobQueue
from ..infrastructure.storage import LocalAssetStorage
from ..library.country_catalog import get_country_library
from ..library.seed import ensure_country_library_projects, ensure_egypt_library, ensure_libya_library
from ..providers.registry import default_provider_registry
from ..services.project_context import ProjectContextStore
from ..services.series_bible import SeriesBibleService
from ..workers.best_take_worker import BestTakeWorker
from ..workers.language_pack_worker import LanguagePackWorker
from ..workers.media_document_worker import MediaDocumentWorker
from ..workers.provider_worker import ProviderGenerationWorker
from ..workers.publish_worker import PublishWorker
from ..workers.qc_worker import QualityControlWorker
from ..workers.render_worker import RenderWorker
from ..workers.repurpose_worker import RepurposeWorker
from ..workers.timeline_worker import TimelineWorker
from ..workers.registry import WorkerRegistry
from .completion_gate import CompletionGate
from .job_executor import ExecutionResult, JobExecutor
from .job_service import JobService
from .production_pipeline import ProductionPipelineOrchestrator
from .queue import JobLease

logger = logging.getLogger(__name__)


class OrchestratorRuntime:
    """Production composition root with durable project/series continuity memory."""

    def __init__(self, repositories: SQLiteRepositories, storage_root: str | Path | None = None) -> None:
        self.repositories = repositories
        self.context = ProjectContextStore(repositories.store)
        self.series_bible = SeriesBibleService(self.context)
        self.assets = SQLiteAssetRepository(repositories.store)
        self.characters = SQLiteCharacterRepository(repositories.store)
        self.locations = SQLiteLocationRepository(repositories.store)
        self.events = SQLiteJobEventRepository(repositories.store)
        self.provider_runs = SQLiteProviderRunRepository(repositories.store)
        self.shot_composition = SQLiteShotCompositionRepository(repositories.store)
        self.queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        root = storage_root or os.getenv("AICF_ASSET_ROOT", "./data/assets")
        self.storage = LocalAssetStorage(root)
        self.workers = WorkerRegistry()
        self.providers = default_provider_registry()

        provider_worker = ProviderGenerationWorker(self.providers, self.storage, self.assets, self.provider_runs)
        provider_worker.initialize()
        self.workers.register(provider_worker, capabilities={"STORY", "CHARACTER", "WORLD", "SCENE", "SHOT", "IMAGE", "TTS"}, worker_id="provider-generation")
        qc = QualityControlWorker(self.storage, self.assets); qc.initialize(); self.workers.register(qc, capabilities={"QC"}, worker_id="quality-control")
        best_take = BestTakeWorker(self.storage, self.assets); best_take.initialize(); self.workers.register(best_take, capabilities={"BEST_TAKE"}, worker_id="best-take")
        timeline = TimelineWorker(self.storage, self.assets); timeline.initialize(); self.workers.register(timeline, capabilities={"TIMELINE"}, worker_id="timeline")
        render = RenderWorker(self.storage, self.assets, ffmpeg_binary=os.getenv("AICF_FFMPEG_BIN", "ffmpeg"), ffprobe_binary=os.getenv("AICF_FFPROBE_BIN", "ffprobe")); render.initialize(); self.workers.register(render, capabilities={"RENDER"}, worker_id="render")
        media = MediaDocumentWorker(self.storage, self.assets); media.initialize(); self.workers.register(media, capabilities={"SUBTITLE", "THUMBNAIL", "METADATA"}, worker_id="media-document")
        language_pack = LanguagePackWorker(self.storage, self.assets); language_pack.initialize(); self.workers.register(language_pack, capabilities={"LANGUAGE_PACK"}, worker_id="language-pack")
        publisher = PublishWorker(self.storage, self.assets); publisher.initialize(); self.workers.register(publisher, capabilities={"PUBLISH"}, worker_id="publish")
        repurpose = RepurposeWorker(self.storage, self.assets); repurpose.initialize(); self.workers.register(repurpose, capabilities={"REPURPOSE"}, worker_id="repurpose")

        self.story_engine = AIStoryEngine(self.providers)
        self.script_engine = AIScriptEngine(self.providers)
        self.scene_planner = AIScenePlanner(self.providers)
        self.job_service = JobService(repositories.jobs)
        self.pipeline = ProductionPipelineOrchestrator(self.job_service, self.queue.enqueue)
        self.completion_gate = CompletionGate(self.assets, self.storage)
        self.executor = JobExecutor(repositories.jobs, self.queue, self.workers, self.events.append, self._on_job_completed, completion_gate=self.completion_gate)
        self.country_library_seed = ensure_country_library_projects(repositories)
        self.library_seed = ensure_egypt_library(repositories)
        self.libya_library_seed = ensure_libya_library(repositories)

    def _on_job_completed(self, job: GenerationJob) -> None:
        """Persist provider outputs and materialize every completed generation in the bible."""
        if job.status is JobStatus.COMPLETED and job.output and job.output.asset_ids:
            try:
                if job.type is JobType.IMAGE and job.target_type == "shot":
                    self.shot_composition.update_generation(job.target_id, status="completed", error="", image_asset_id=job.output.asset_ids[0])
                elif job.type is JobType.TTS and job.target_type == "shot_character":
                    self.shot_composition.set_voice_audio_asset(job.target_id, job.output.asset_ids[0])
            except Exception:
                logger.exception("Failed to bind completed %s job %s to target %s/%s", job.type.value, job.id, job.target_type, job.target_id)
        if job.project_id:
            event = {
                "jobId": job.id, "type": job.type.value, "targetType": job.target_type, "targetId": job.target_id,
                "status": job.status.value, "assetIds": list(job.output.asset_ids) if job.output else [],
                "errorCode": job.error_code, "errorMessage": job.error_message,
            }
            try:
                self.series_bible.record_job(job.project_id, event)
            except Exception:
                logger.exception("Failed to materialize job %s in series bible", job.id)
            try:
                self.context.append_event(job.project_id, "job.completed" if job.status is JobStatus.COMPLETED else "job.finished", event, entity_type="job", entity_id=job.id)
            except Exception:
                logger.exception("Failed to append project context event for job %s", job.id)
        self.pipeline.on_completed(job)

    def _resolve_library_scope(self, brief: ContentBrief) -> tuple[str, str]:
        country_id = brief.country_id or "egypt"
        country = get_country_library(country_id)
        if country is None:
            raise ValueError("COUNTRY_LIBRARY_NOT_FOUND")
        expected_library_id = str(country["libraryId"])
        library_id = brief.library_id or expected_library_id
        if library_id != expected_library_id:
            raise ValueError("COUNTRY_LIBRARY_MISMATCH")
        return country_id, library_id

    def plan_content(self, brief: ContentBrief, model_id: str | None = None) -> StoryPlan:
        self._resolve_library_scope(brief)
        project_id = brief.project_id
        characters = tuple(c for cid in brief.character_ids if (c := self.characters.get(cid)) is not None and (project_id is None or c.project_id == project_id))
        locations = tuple(l for lid in brief.location_ids if (l := self.locations.get(lid)) is not None and (project_id is None or l.project_id == project_id))
        if brief.character_ids and not characters:
            raise ValueError("CHARACTERS_NOT_FOUND_IN_PROJECT")
        if brief.location_ids and not locations:
            raise ValueError("LOCATIONS_NOT_FOUND_IN_PROJECT")
        context = self.context.get(project_id) if project_id else {"version": 0, "context": {}}
        enriched_context = dict(brief.production_context)
        enriched_context["persistentSeriesContext"] = context["context"]
        enriched_context["seriesBible"] = self.series_bible.snapshot(project_id) if project_id else {}
        enriched_context["contextVersion"] = context["version"]
        effective_brief = replace(brief, production_context=enriched_context)
        if project_id:
            self.context.append_event(project_id, "content.plan.requested", {
                "topic": brief.topic, "characterIds": list(brief.character_ids), "locationIds": list(brief.location_ids),
                "language": brief.language, "durationSeconds": brief.duration_seconds, "style": brief.style,
                "contextVersion": context["version"],
            }, entity_type="content_plan", entity_id=project_id)
        story = self.story_engine.generate(effective_brief, model_id, characters, locations)
        script = self.script_engine.generate(effective_brief, story, model_id)
        return self.scene_planner.plan(effective_brief, script, model_id)

    def execute_next(self, worker_id: str = "auto") -> ExecutionResult | None:
        claimed = self.queue.claim_next(worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        selected_worker = worker_id if worker_id != "auto" else self.workers.resolve_for_job(job.type)
        return self.executor.execute_claimed(job, lease, worker_id=selected_worker)

    def execute_job(self, job_id: str, worker_id: str = "auto") -> ExecutionResult | None:
        claimed = self.queue.claim(job_id, worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        selected_worker = worker_id if worker_id != "auto" else self.workers.resolve_for_job(job.type)
        return self.executor.execute_claimed(job, lease, worker_id=selected_worker)

    def cancel_job(self, job_id: str) -> object:
        job = self.repositories.jobs.get(job_id)
        if job is None:
            raise KeyError("JOB_NOT_FOUND")
        if job.status is JobStatus.RUNNING:
            try:
                worker_id = self.workers.resolve_for_job(job.type)
                self.workers.get(worker_id).cancel(job.id)
            except Exception:
                logger.exception("Best-effort worker cancellation failed for job %s", job_id)
        return self.job_service.cancel(job_id)

    def heartbeat(self, job_id: str, lease_id: str, worker_id: str) -> None:
        if self.repositories.jobs.get(job_id) is None:
            raise KeyError("JOB_NOT_FOUND")
        self.queue.heartbeat(JobLease(job_id=job_id, worker_id=worker_id, lease_id=lease_id, expires_at=""))

    def recover_expired(self) -> int:
        return self.queue.release_expired()
