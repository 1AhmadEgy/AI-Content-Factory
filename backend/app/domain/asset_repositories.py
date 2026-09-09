from abc import ABC, abstractmethod

from .assets import Asset


class AssetRepository(ABC):
    @abstractmethod
    def create(self, asset: Asset) -> Asset: ...

    @abstractmethod
    def get(self, asset_id: str) -> Asset | None: ...
