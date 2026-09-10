from __future__ import annotations

import os
from pathlib import Path

from ..application.ai_scene_planner import AIScenePlanner
from ..application.ai_script_engine import AIScriptEngine
from ..application.ai_story_engine import AIStoryEngine
from ..domain.content import ContentBrief, StoryPlan
from ..infrastructure.asset_repository import SQLiteAssetRepository
from ..infrastructure.job_event_repository import SQLiteJobEventRepository
from ..infrastructure.sqlite import SQLiteRepositories
from ..infrastructure.sqlite_queue import SQLiteJobQueue
from ..infrastructure.storage import LocalAssetStorage
from ..providers.registry import default_provider_registry
from ..workers.best_take_worker import BestTakeWorker
from ..workers.media_document_worker import MediaDocumentWorker
from ..workers.mock_worker import DeterministicMockWorker
from ..workers.provider_worker import ProviderGenerationWorker
from ..workers.publish_worker import PublishWorker
from ..workers.qc_worker import QualityControlWorker
from ..workers.render_worker import RenderWorker
from ..workers.timeline_worker import TimelineWorker
from ..workers.registry import WorkerRegistry
from .content_pipeline import ContentPipelineOrchestrator
from .job_executor import ExecutionResult, JobExecutor
from .job_service import JobService
from .queue import JobLease


class OrchestratorRuntime:
    """Local-first composition root for persisted execution and AI planning."""

    def __init__(self, repositories: SQLiteRepositories, storage_root: str | Path | None = None) -> None:
        self.repositories = repositories
        self.assets = SQLiteAssetRepository(repositories.store)
        self.events = SQLiteJobEventRepository(repositories.store)
        self.queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        root = storage_root or os.getenv("AICF_ASSET_ROOT", "./data/assets")
        self.storage = LocalAssetStorage(root)
        self.workers = WorkerRegistry()

        self.providers = default_provider_registry()
        provider_worker = ProviderGenerationWorker(self.providers, self.storage, self.assets)
        provider_worker.initialize()
        self.workers.register(provider_worker, capabilities={"IMAGE", "VIDEO", "AUDIO", "DOCUMENT", "SUBTITLE"}, worker_id="provider-generation")
        mock = DeterministicMockWorker(self.storage, self.assets)
        mock.initialize()
        self.workers.register(mock, capabilities={"IMAGE", "VIDEO", "AUDIO", "DOCUMENT", "SUBTITLE"}, worker_id="mock")
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
        publisher = PublishWorker(self.storage, self.assets)
        publisher.initialize()
        self.workers.register(publisher, capabilities={"PUBLISH"}, worker_id="publish")

        self.story_engine = AIStoryEngine(self.providers)
        self.script_engine = AIScriptEngine(self.providers)
        self.scene_planner = AIScenePlanner(self.providers)
        self.pipeline = ContentPipelineOrchestrator(JobService(repositories.jobs), self.queue.enqueue)
        self.executor = JobExecutor(repositories.jobs, self.queue, self.workers, self.events.append, self.pipeline.on_completed)

    def plan_content(self, brief: ContentBrief, model_id: str | None = None) -> StoryPlan:
        story = self.story_engine.generate(brief, model_id)
        script = self.script_engine.generate(brief, story, model_id)
        return self.scene_planner.plan(brief, script, model_id)

    def execute_next(self, worker_id: str = "auto") -> ExecutionResult | None:
        claimed = self.queue.claim_next(worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        selected_worker = worker_id if worker_id != "auto" else self.workers.resolve_for_job(job.type)
        return self.executor.execute_claimed(job, lease, worker_id=selected_worker)

    def heartbeat(self, job_id: str, lease_id: str, worker_id: str) -> None:
        if self.repositories.jobs.get(job_id) is None:
            raise KeyError("JOB_NOT_FOUND")
        self.queue.heartbeat(JobLease(job_id=job_id, worker_id=worker_id, lease_id=lease_id, expires_at=""))

    def recover_expired(self) -> int:
        return self.queue.release_expired()
