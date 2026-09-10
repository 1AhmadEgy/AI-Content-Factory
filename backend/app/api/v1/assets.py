from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from ...domain.assets import AssetStatus
from ...infrastructure.asset_repository import SQLiteAssetRepository


def _serialize(asset) -> dict:
    return {
        "id": asset.id,
        "projectId": asset.project_id,
        "type": asset.type.value,
        "path": asset.path,
        "mimeType": asset.mime_type,
        "sizeBytes": asset.size_bytes,
        "sha256": asset.sha256,
        "status": asset.status.value,
        "createdAt": asset.created_at.isoformat(),
        "provenance": {
            "provider": asset.provenance.provider,
            "model": asset.provenance.model,
            "prompt": asset.provenance.prompt,
            "negativePrompt": asset.provenance.negative_prompt,
            "seed": asset.provenance.seed,
            "sourceAssetIds": asset.provenance.source_asset_ids,
            "jobId": asset.provenance.job_id,
            "licenseStatus": asset.provenance.license_status.value,
            "metadata": asset.provenance.metadata,
        },
    }


def build_router(repository: SQLiteAssetRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

    @router.get("")
    def list_assets(request: Request, projectId: str | None = Query(default=None), type: str | None = Query(default=None), page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=200)) -> dict:
        sql = "SELECT * FROM assets WHERE 1=1"
        args: list[object] = []
        if projectId:
            sql += " AND project_id = ?"; args.append(projectId)
        if type:
            sql += " AND type = ?"; args.append(type.upper())
        sql += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"; args.extend([pageSize, (page - 1) * pageSize])
        with repository.store._lock:
            rows = repository.store.connection.execute(sql, tuple(args)).fetchall()
            count_sql = "SELECT COUNT(*) FROM assets WHERE 1=1" + (" AND project_id = ?" if projectId else "") + (" AND type = ?" if type else "")
            count_args = ([projectId] if projectId else []) + ([type.upper()] if type else [])
            total = repository.store.connection.execute(count_sql, tuple(count_args)).fetchone()[0]
        from ...infrastructure.asset_repository import SQLiteAssetRepository as _AR
        items = [_serialize(_AR.get(repository, row["id"])) for row in rows]
        return {"data": items, "pagination": {"page": page, "pageSize": pageSize, "total": total, "hasNext": page * pageSize < total}, "requestId": request.state.request_id}

    @router.get("/{asset_id}")
    def get_asset(asset_id: str, request: Request) -> dict:
        asset = repository.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        return {"data": _serialize(asset), "requestId": request.state.request_id}

    @router.get("/{asset_id}/metadata")
    def metadata(asset_id: str, request: Request) -> dict:
        asset = repository.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        return {"data": {"id": asset.id, "mimeType": asset.mime_type, "sizeBytes": asset.size_bytes, "sha256": asset.sha256, "provenance": _serialize(asset)["provenance"]}, "requestId": request.state.request_id}

    @router.get("/{asset_id}/download")
    def download(asset_id: str):
        asset = repository.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        if asset.status is not AssetStatus.READY:
            raise HTTPException(status_code=409, detail="ASSET_NOT_READY")
        path = Path(asset.path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="ASSET_FILE_NOT_FOUND")
        return FileResponse(path=str(path), media_type=asset.mime_type, filename=path.name)

    return router
