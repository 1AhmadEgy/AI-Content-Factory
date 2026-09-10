from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..domain.assets import AssetStatus
from ..domain.jobs import GenerationJob
from ..domain.qc import QcResult, evaluate_asset
from ..domain.asset_repositories import AssetRepository
from ..infrastructure.storage import LocalAssetStorage


@dataclass(frozen=True, slots=True)
class CompletionGateResult:
    allowed: bool
    code: str | None = None
    message: str | None = None
    qc_results: tuple[QcResult, ...] = field(default_factory=tuple)


class CompletionGate:
    """Final server-side gate before a generation job may become COMPLETED."""

    def __init__(
        self,
        assets: AssetRepository,
        storage: LocalAssetStorage,
        qc_evaluator: Callable[..., QcResult] = evaluate_asset,
    ) -> None:
        self.assets = assets
        self.storage = storage
        self.qc_evaluator = qc_evaluator

    def check(self, job: GenerationJob) -> CompletionGateResult:
        if job.output is None or not job.output.asset_ids:
            return CompletionGateResult(False, "MISSING_OUTPUT_ASSET", "No persisted output assets were returned.")

        results: list[QcResult] = []
        for asset_id in job.output.asset_ids:
            asset = self.assets.get(asset_id)
            if asset is None:
                return CompletionGateResult(False, "ASSET_NOT_PERSISTED", f"Output asset is not persisted: {asset_id}")
            if asset.status is not AssetStatus.READY:
                return CompletionGateResult(False, "ASSET_NOT_READY", f"Output asset is not READY: {asset_id}")
            if asset.project_id != job.project_id:
                return CompletionGateResult(False, "ASSET_PROJECT_MISMATCH", f"Output asset belongs to another project: {asset_id}")
            if asset.provenance.job_id != job.id:
                return CompletionGateResult(False, "PROVENANCE_NOT_PERSISTED", f"Output asset provenance does not reference job: {asset_id}")

            try:
                readable = self.storage.verify(asset)
            except (OSError, IOError, ValueError):
                readable = False

            qc = self.qc_evaluator(
                asset_id=asset.id,
                readable=readable,
                size_bytes=asset.size_bytes,
                license_status=asset.provenance.license_status.value,
            )
            results.append(qc)
            if not qc.passed or qc.blocked:
                return CompletionGateResult(
                    False,
                    "QC_BLOCKED",
                    f"Required QC failed for asset: {asset_id}",
                    tuple(results),
                )

        return CompletionGateResult(True, qc_results=tuple(results))
