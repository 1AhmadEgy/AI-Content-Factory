from __future__ import annotations

import hashlib
import json
import math
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class BestTakeWorker(Worker):
    """Select the highest-scoring valid take and persist the decision."""

    worker_type = "best-take"

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
        candidates = job.input.parameters.get("candidates", [])
        if not isinstance(candidates, list) or not candidates:
            return JobExecutionResult(False, error_code="BEST_TAKE_NO_CANDIDATES", error_message="No candidates supplied")

        valid: list[dict[str, object]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            asset_id = str(candidate.get("assetId", "")).strip()
            asset = self.assets.get(asset_id) if asset_id else None
            try:
                score = float(candidate.get("score", 0))
            except (TypeError, ValueError):
                continue
            if not asset or asset.status is not AssetStatus.READY or asset.project_id != job.project_id:
                continue
            if asset.type is not AssetType.VIDEO or not math.isfinite(score):
                continue
            valid.append({**candidate, "assetId": asset_id, "score": score})

        if not valid:
            return JobExecutionResult(False, error_code="BEST_TAKE_NO_VALID_CANDIDATES", error_message="No valid video candidates")

        winner = max(valid, key=lambda candidate: float(candidate["score"]))
        winner_id = str(winner["assetId"])
        winner_score = float(winner["score"])
        decision = {"selectedAssetId": winner_id, "score": winner_score, "candidates": valid}
        payload = (json.dumps(decision, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        decision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"best-take:{job.id}:{digest}"))
        asset = Asset(
            id=decision_id,
            project_id=job.project_id,
            type=AssetType.DOCUMENT,
            path=path,
            mime_type="application/json; charset=utf-8",
            size_bytes=size,
            sha256=digest,
            status=AssetStatus.READY,
            provenance=build_provenance(job, source_asset_ids=[winner_id], metadata={"selectedAssetId": winner_id, "score": winner_score}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(
            success=True,
            asset_ids=[decision_id],
            metrics={"score": winner_score, "selectedAssetId": winner_id},
            provider_run_id=f"best-take-{job.id}",
        )

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
