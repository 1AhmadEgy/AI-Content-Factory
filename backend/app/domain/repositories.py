from abc import ABC, abstractmethod
from dataclasses import dataclass

from .assets import Asset, AssetStatus
from .jobs import GenerationJob, JobStatus
from .projects import Episode, Project, Scene, Shot
from .provider_runs import ProviderRun


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    """Outcome of an atomic idempotent resource creation attempt."""

    job: GenerationJob | None
    existing_resource_id: str | None = None
    conflict: bool = False
    replayed: bool = False


class ProjectRepository(ABC):
    @abstractmethod
    def create(self, project: Project) -> Project: ...

    @abstractmethod
    def get(self, project_id: str) -> Project | None: ...


class EpisodeRepository(ABC):
    @abstractmethod
    def create(self, episode: Episode) -> Episode: ...

    @abstractmethod
    def get(self, episode_id: str) -> Episode | None: ...


class SceneRepository(ABC):
    @abstractmethod
    def create(self, scene: Scene) -> Scene: ...

    @abstractmethod
    def get(self, scene_id: str) -> Scene | None: ...


class ShotRepository(ABC):
    @abstractmethod
    def create(self, shot: Shot) -> Shot: ...

    @abstractmethod
    def get(self, shot_id: str) -> Shot | None: ...


class JobRepository(ABC):
    @abstractmethod
    def create(self, job: GenerationJob) -> GenerationJob: ...

    @abstractmethod
    def get(self, job_id: str) -> GenerationJob | None: ...

    @abstractmethod
    def update(self, job: GenerationJob) -> GenerationJob: ...

    @abstractmethod
    def update_if_current(
        self,
        job: GenerationJob,
        expected_status: JobStatus,
        expected_attempt: int,
    ) -> bool: ...

    def create_with_idempotency(
        self,
        job: GenerationJob,
        *,
        key: str,
        operation: str,
        fingerprint: str,
    ) -> IdempotencyResult | None:
        """Optionally atomically create a job and idempotency record."""
        return None

    @abstractmethod
    def list_by_parent(self, parent_job_id: str) -> list[GenerationJob]: ...

    @abstractmethod
    def list(
        self,
        *,
        project_id: str | None = None,
        status: JobStatus | None = None,
        limit: int = 50,
    ) -> list[GenerationJob]: ...


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


class ProviderRunRepository(ABC):
    @abstractmethod
    def create(self, run: ProviderRun) -> ProviderRun | None: ...

    @abstractmethod
    def complete(
        self,
        run_id: str,
        *,
        status: str,
        response_metadata: dict | None = None,
        error_code: str | None = None,
    ) -> ProviderRun: ...

    @abstractmethod
    def get(self, run_id: str) -> ProviderRun: ...

    @abstractmethod
    def list_for_job(self, job_id: str, limit: int = 50) -> list[ProviderRun]: ...
