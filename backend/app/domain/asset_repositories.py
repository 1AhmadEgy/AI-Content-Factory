from abc import ABC, abstractmethod

from .assets import Asset, AssetStatus


class AssetRepository(ABC):
    @abstractmethod
    def create(self, asset: Asset) -> Asset: ...

    @abstractmethod
    def get(self, asset_id: str) -> Asset | None: ...

    @abstractmethod
    def update(self, asset: Asset) -> Asset: ...

    @abstractmethod
    def list(
        self,
        *,
        project_id: str | None = None,
        asset_type: str | None = None,
        status: AssetStatus | None = None,
        limit: int = 100,
    ) -> list[Asset]: ...
