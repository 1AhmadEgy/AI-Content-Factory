from __future__ import annotations

from uuid import uuid4

from ..domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from .storage import LocalAssetStorage


class AssetService:
    def __init__(self, storage: LocalAssetStorage) -> None:
        self.storage = storage

    def create_from_bytes(
        self,
        *,
        project_id: str,
        asset_type: AssetType,
        data: bytes,
        mime_type: str,
        provenance: AssetProvenance | None = None,
    ) -> Asset:
        sha256, path, size = self.storage.put_bytes(data)
        asset = Asset(
            id=str(uuid4()),
            project_id=project_id,
            type=asset_type,
            path=path,
            mime_type=mime_type,
            size_bytes=size,
            sha256=sha256,
            status=AssetStatus.READY,
            provenance=provenance or AssetProvenance(license_status=LicenseStatus.UNKNOWN),
        )
        return asset

    def verify(self, asset: Asset) -> bool:
        return self.storage.verify(asset)

    def mark_corrupted(self, asset: Asset) -> Asset:
        asset.status = AssetStatus.CORRUPTED
        return asset

    def mark_deleted(self, asset: Asset) -> Asset:
        asset.status = AssetStatus.DELETED
        return asset
