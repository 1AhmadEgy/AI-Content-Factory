from __future__ import annotations

import logging
import os
from pathlib import Path

from ..application.ai_scene_planner import AIScenePlanner
from ..application.ai_script_engine import AIScriptEngine
from ..application.ai_story_engine import AIStoryEngine
from ..domain.content import ContentBrief, StoryPlan
from ..domain.jobs import JobStatus
from ..infrastructure.asset_repository import SQLiteAssetRepository
from ..infrastructure.character_repository import SQLiteCharacterRepository
from ..infrastructure.location_repository import SQLiteLocationRepository
from ..infrastructure.job_event_repository import SQLiteJobEventRepository
from ..infrastructure.provider_run_repository import SQLiteProviderRunRepository
from ..infrastructure.sqlite import SQLiteRepositories
from ..infrastructure.sqlite_queue import SQLiteJobQueue
from ..infrastructure.storage import LocalAssetStorage
from ..library.country_catalog import get_country_library
from ..library.seed import ensure_country_library_projects, ensure_egypt_library, ensure_libya_library
from ..providers.registry import default_provider_registry
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
    """Composition root using only configured providers and durable workers."""

    def __init__(self, repositories: SQLiteRepositories, storage_root: str | Path | None = None) -> None:
        self.repositories = repositories
        self.assets = SQLiteAssetRepository(repositories.store)
        self.characters = SQLiteCharacterRepository(repositories.store)
        self.locations = SQLiteLocationRepository(repositories.store)
        self.events = SQLiteJobEventRepository(repositories.store)
        self.provider_runs = SQLiteProviderRunRepository(repositories.store)
        self.queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        root = storage_root or os.getenv("AICF_ASSET_ROOT", "./data/assets")
        self.storage = LocalAssetStorage(root)
        self.workers = WorkerRegistry()
        self.providers = default_provider_registry()

        provider_worker = ProviderGenerationWorker(self.providers, self.storage, self.assets, self.provider_runs)
        provider_worker.initialize()
        self.workers.register(provider_worker, capabilities={"STORY", "CHARACTER", "WORLD", "SCENE", "SHOT", "IMAGE", "VIDEO", "TTS", "LIPSYNC", "MUSIC", "SFX", "UPSCALE", "INTERPOLATION"}, worker_id="provider-generation")

        qc = QualityControlWorker(self.storage, self.assets)
        qc.initialize()
        self.workers.register(qc, capabilities={"DOCUMENT"}, worker_id="quality-control")
        best_take = BestTakeWorker(self.storage, self.assets)
        best_take.initialize()
        self.workers.register(best_take, capabilities={"DOCUMENT"}, worker_id="best-take")
        timeline = TimelineWorker(self.storage, self.assets)
        timeline.initialize()
        self.workers.register(timeline, capabilities={"DOCUMENT"}, worker_id="timeline")
        render = RenderWorker(self.storage, self.assets)
        render.initialize()
        self.workers.register(render, capabilities={"VIDEO"}, worker_id="render")
        media = MediaDocumentWorker(self.storage, self.assets)
        media.initialize()
        self.workers.register(media, capabilities={"SUBTITLE", "THUMBNAIL", "METADATA"}, worker_id="media-document")
        language_pack = LanguagePackWorker(self.storage, self.assets)
        language_pack.initialize()
        self.workers.register(language_pack, capabilities={"LANGUAGE_PACK"}, worker_id="language-pack")
        publisher = PublishWorker(self.storage, self.assets)
        publisher.initialize()
        self.workers.register(publisher, capabilities={"PUBLISH"}, worker_id="publish")
        repurpose = RepurposeWorker(self.storage, self.assets)
        repurpose.initialize()
        self.workers.register(repurpose, capabilities={"REPURPOSE"}, worker_id="repurpose")

        self.story_engine = AIStoryEngine(self.providers)
        self.script_engine = AIScriptEngine(self.providers)
        self.scene_planner = AIScenePlanner(self.providers)
        self.job_service = JobService(repositories.jobs)
        self.pipeline = ProductionPipelineOrchestrator(self.job_service, self.queue.enqueue)
        self.completion_gate = CompletionGate(self.assets, self.storage)
        self.executor = JobExecutor(repositories.jobs, self.queue, self.workers, self.events.append, self.pipeline.on_completed, completion_gate=self.completion_gate)
        self.country_library_seed = ensure_country_library_projects(repositories)
        self.library_seed = ensure_egypt_library(repositories)
        self.libya_library_seed = ensure_libya_library(repositories)

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

    @staticmethod
    def _validate_identity_continuity(story: StoryPlan, characters: tuple, locations: tuple) -> None:
        allowed_characters = {c.id for c in characters}
        allowed_locations = {l.id for l in locations}
        for scene in story.scenes:
            for shot in scene.shots:
                if set(shot.character_ids) - allowed_characters:
                    raise ValueError("CHARACTER_CONTINUITY_VIOLATION")
                if set(shot.location_ids) - allowed_locations:
                    raise ValueError("LOCATION_CONTINUITY_VIOLATION")

    def plan_content(self, brief: ContentBrief, model_id: str | None = None) -> StoryPlan:
        self._resolve_library_scope(brief)
        project_id = brief.project_id or brief.library_id
        characters = tuple(c for cid in brief.character_ids if (c := self.characters.get(cid)) is not None and c.project_id == project_id)
        locations = tuple(l for lid in brief.location_ids if (l := self.locations.get(lid)) is not None and l.project_id == project_id)
        if len(characters) != len(brief.character_ids):
            raise ValueError("CHARACTER_SCOPE_VIOLATION")
        if len(locations) != len(brief.location_ids):
            raise ValueError("LOCATION_SCOPE_VIOLATION")
        story = self.story_engine.generate(brief, model_id, characters, locations)
        self._validate_identity_continuity(story, characters, locations)
        script = self.script_engine.generate(brief, story, model_id)
        self._validate_identity_continuity(script, characters, locations)
        planned = self.scene_planner.plan(brief, script, model_id)
        self._validate_identity_continuity(planned, characters, locations)
        return planned

    def _execute_claimed(self, job, lease, worker_id: str) -> ExecutionResult:
        self.queue.start(lease)
        job = self.repositories.jobs.get(job.id) or job
        return self.executor.execute_claimed(job, lease, worker_id=worker_id)

    def execute_next(self, worker_id: str = "auto") -> ExecutionResult | None:
        claimed = self.queue.claim_next(worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        selected_worker = worker_id if worker_id != "auto" else self.workers.resolve_for_job(job.type)
        return self._execute_claimed(job, lease, selected_worker)

    def execute_job(self, job_id: str, worker_id: str = "auto") -> ExecutionResult | None:
        claimed = self.queue.claim(job_id, worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        selected_worker = worker_id if worker_id != "auto" else self.workers.resolve_for_job(job.type)
        return self._execute_claimed(job, lease, selected_worker)

    def cancel_job(self, job_id: str) -> object:
        job = self.repositories.jobs.get(job_id)
        if job is None:
            raise KeyError("JOB_NOT_FOUND")
        if job.status is JobStatus.RUNNING:
            try:
                worker_id = self.workers.resolve_for_job(job.type)
                self.workers.get(worker_id).cancel(job.id)
            except Exception:
                logger.exception("Best-effort worker cancellation failed for job %s", job.id)
        return self.job_service.cancel(job_id)

    def heartbeat(self, job_id: str, lease_id: str, worker_id: str) -> None:
        if self.repositories.jobs.get(job_id) is None:
            raise KeyError("JOB_NOT_FOUND")
        self.queue.heartbeat(JobLease(job_id=job_id, worker_id=worker_id, lease_id=lease_id, expires_at=""))

    def recover_expired(self) -> int:
        return self.queue.release_expired()
