from __future__ import annotations

import os
from pathlib import Path

from ..infrastructure.asset_repository import SQLiteAssetRepository
from ..infrastructure.job_event_repository import SQLiteJobEventRepository
from ..infrastructure.sqlite import SQLiteRepositories
from ..infrastructure.sqlite_queue import SQLiteJobQueue
from ..infrastructure.storage import LocalAssetStorage
from ..workers.mock_worker import DeterministicMockWorker
from ..workers.registry import WorkerRegistry
from .job_executor import ExecutionResult, JobExecutor


class OrchestratorRuntime:
    """Local-first composition root for the persisted job execution path."""

    def __init__(self, repositories: SQLiteRepositories, storage_root: str | Path | None = None) -> None:
        self.repositories = repositories
        self.assets = SQLiteAssetRepository(repositories.store)
        self.events = SQLiteJobEventRepository(repositories.store)
        self.queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        root = storage_root or os.getenv("AICF_ASSET_ROOT", "./data/assets")
        self.storage = LocalAssetStorage(root)
        self.workers = WorkerRegistry()
        mock = DeterministicMockWorker(self.storage, self.assets)
        mock.initialize()
        self.workers.register(mock, capabilities={"IMAGE", "VIDEO", "AUDIO", "DOCUMENT", "SUBTITLE"}, worker_id="mock")
        self.executor = JobExecutor(repositories.jobs, self.queue, self.workers, self.events.append)

    def execute_next(self, worker_id: str = "mock") -> ExecutionResult | None:
        claimed = self.queue.claim_next(worker_id)
        if claimed is None:
            return None
        job, lease = claimed
        return self.executor.execute_claimed(job, lease, worker_id=worker_id)
