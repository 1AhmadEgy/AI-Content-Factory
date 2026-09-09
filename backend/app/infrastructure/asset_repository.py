from __future__ import annotations

import json
from threading import RLock

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from .sqlite import SQLiteStore, _dt, _json, _parse_dt


class SQLiteAssetRepository(AssetRepository):
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self._lock = RLock()
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                """CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id)"
            )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256)"
            )

    def create(self, asset: Asset) -> Asset:
        provenance = {
            "provider": asset.provenance.provider,
            "model": asset.provenance.model,
            "prompt": asset.provenance.prompt,
            "negativePrompt": asset.provenance.negative_prompt,
            "seed": asset.provenance.seed,
            "sourceAssetIds": asset.provenance.source_asset_ids,
            "jobId": asset.provenance.job_id,
            "licenseStatus": asset.provenance.license_status.value,
            "metadata": asset.provenance.metadata,
        }
        self.store._insert(
            """INSERT INTO assets(
                id,project_id,type,path,mime_type,size_bytes,sha256,status,provenance_json,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                asset.id, asset.project_id, asset.type.value, asset.path, asset.mime_type,
                asset.size_bytes, asset.sha256, asset.status.value, _json(provenance), _dt(asset.created_at),
            ),
        )
        return asset

    def get(self, asset_id: str) -> Asset | None:
        row = self.store._get("assets", asset_id)
        if row is None:
            return None
        provenance = json.loads(row["provenance_json"])
        return Asset(
            id=row["id"],
            project_id=row["project_id"],
            type=AssetType(row["type"]),
            path=row["path"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            status=AssetStatus(row["status"]),
            provenance=AssetProvenance(
                provider=provenance.get("provider"),
                model=provenance.get("model"),
                prompt=provenance.get("prompt"),
                negative_prompt=provenance.get("negativePrompt"),
                seed=provenance.get("seed"),
                source_asset_ids=provenance.get("sourceAssetIds", []),
                job_id=provenance.get("jobId"),
                license_status=LicenseStatus(provenance.get("licenseStatus", LicenseStatus.UNKNOWN.value)),
                metadata=provenance.get("metadata", {}),
            ),
            created_at=_parse_dt(row["created_at"]),
        )
