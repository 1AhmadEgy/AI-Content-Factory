from __future__ import annotations

from abc import ABC, abstractmethod

from .characters import CharacterProfile


class CharacterRepository(ABC):
    @abstractmethod
    def create(self, character: CharacterProfile) -> CharacterProfile: ...

    @abstractmethod
    def get(self, character_id: str) -> CharacterProfile | None: ...

    @abstractmethod
    def update(self, character: CharacterProfile) -> CharacterProfile: ...

    @abstractmethod
    def delete(self, character_id: str) -> bool: ...

    @abstractmethod
    def list(self, *, project_id: str | None = None, query: str | None = None, limit: int = 100) -> list[CharacterProfile]: ...
