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
            self.store.connection.execute("""CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                type TEXT NOT NULL, path TEXT NOT NULL, mime_type TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL, status TEXT NOT NULL, provenance_json TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id)")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_assets_project_type_status ON assets(project_id,type,status)")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256)")

    @staticmethod
    def _provenance(asset: Asset) -> str:
        p = asset.provenance
        return _json({"provider": p.provider, "model": p.model, "prompt": p.prompt,
                      "negativePrompt": p.negative_prompt, "seed": p.seed,
                      "sourceAssetIds": p.source_asset_ids, "jobId": p.job_id,
                      "licenseStatus": p.license_status.value, "metadata": p.metadata})

    @staticmethod
    def _from_row(row) -> Asset:
        p = json.loads(row["provenance_json"])
        return Asset(id=row["id"], project_id=row["project_id"], type=AssetType(row["type"]),
                     path=row["path"], mime_type=row["mime_type"], size_bytes=row["size_bytes"],
                     sha256=row["sha256"], status=AssetStatus(row["status"]),
                     provenance=AssetProvenance(provider=p.get("provider"), model=p.get("model"),
                         prompt=p.get("prompt"), negative_prompt=p.get("negativePrompt"), seed=p.get("seed"),
                         source_asset_ids=p.get("sourceAssetIds", []), job_id=p.get("jobId"),
                         license_status=LicenseStatus(p.get("licenseStatus", LicenseStatus.UNKNOWN.value)),
                         metadata=p.get("metadata", {})), created_at=_parse_dt(row["created_at"]))

    def create(self, asset: Asset) -> Asset:
        self.store._insert("INSERT INTO assets(id,project_id,type,path,mime_type,size_bytes,sha256,status,provenance_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (asset.id, asset.project_id, asset.type.value, asset.path, asset.mime_type, asset.size_bytes,
                            asset.sha256, asset.status.value, self._provenance(asset), _dt(asset.created_at)))
        return asset

    def get(self, asset_id: str) -> Asset | None:
        row = self.store._get("assets", asset_id)
        return self._from_row(row) if row else None

    def update(self, asset: Asset) -> Asset:
        with self.store._lock, self.store.connection:
            cur = self.store.connection.execute("UPDATE assets SET project_id=?,type=?,path=?,mime_type=?,size_bytes=?,sha256=?,status=?,provenance_json=? WHERE id=?",
                (asset.project_id, asset.type.value, asset.path, asset.mime_type, asset.size_bytes, asset.sha256,
                 asset.status.value, self._provenance(asset), asset.id))
            if cur.rowcount != 1:
                raise KeyError(f"Asset not found: {asset.id}")
        return asset

    def list(self, *, project_id: str | None = None, asset_type: str | None = None,
             status: AssetStatus | None = None, limit: int = 100) -> list[Asset]:
        limit = max(1, min(limit, 500)); clauses=[]; params=[]
        if project_id: clauses.append("project_id=?"); params.append(project_id)
        if asset_type: clauses.append("type=?"); params.append(asset_type.value if isinstance(asset_type, AssetType) else asset_type)
        if status: clauses.append("status=?"); params.append(status.value)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self.store._lock:
            rows = self.store.connection.execute(f"SELECT * FROM assets{where} ORDER BY created_at DESC,id DESC LIMIT ?", (*params, limit)).fetchall()
        return [self._from_row(row) for row in rows]
