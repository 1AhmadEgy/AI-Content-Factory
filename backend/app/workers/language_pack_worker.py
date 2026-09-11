from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class LanguagePackWorker(Worker):
    """Persist an immutable multilingual episode pack as a provenance-tracked asset."""

    worker_type = "language-pack"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets = storage, assets
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is not JobType.LANGUAGE_PACK:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)

        context.report_progress(0.1, "language_pack_prepare")
        parameters = deepcopy(job.input.parameters)
        source = parameters.get("source")
        variants = parameters.get("variants")
        if not isinstance(source, dict):
            return JobExecutionResult(False, error_code="LANGUAGE_PACK_SOURCE_REQUIRED", error_message="source must be an object")
        if not isinstance(variants, dict) or not variants:
            return JobExecutionResult(False, error_code="LANGUAGE_PACK_VARIANTS_REQUIRED", error_message="variants must be a non-empty object")

        source_hash = hashlib.sha256(
            json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        pack = {
            "schemaVersion": 1,
            "episodeId": parameters.get("episodeId"),
            "sourceLanguage": parameters.get("sourceLanguage") or source.get("sourceLanguage") or source.get("language"),
            "targetLanguages": list(variants.keys()),
            "sourceFingerprint": source_hash,
            "sourcePreserved": True,
            "immutableSource": True,
            "version": int(parameters.get("version", 1)),
            "variants": variants,
            "errors": list(parameters.get("errors") or []),
        }
        payload = (json.dumps(pack, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        context.report_progress(0.65, "language_pack_persist")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"language-pack:{job.project_id}:{digest}"))
        self.assets.create(
            Asset(
                asset_id,
                job.project_id,
                AssetType.DOCUMENT,
                path,
                "application/vnd.aicf.language-pack+json; charset=utf-8",
                size,
                digest,
                AssetStatus.READY,
                build_provenance(
                    job,
                    source_asset_ids=list(job.input.reference_asset_ids),
                    metadata={"worker": self.worker_type, "sourceFingerprint": source_hash, "languageCount": len(variants)},
                    license_status=LicenseStatus.VERIFIED,
                ),
            )
        )
        context.report_progress(1.0, "completed")
        return JobExecutionResult(
            True,
            [asset_id],
            {"bytes": size, "languageCount": len(variants), "sourceFingerprint": source_hash},
            f"{self.worker_type}-{job.id}",
        )

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
