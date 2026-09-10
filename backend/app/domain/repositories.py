from abc import ABC, abstractmethod
from .jobs import GenerationJob, JobStatus
from .projects import Episode, Project, Scene, Shot


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
    def list_by_parent(self, parent_job_id: str) -> list[GenerationJob]: ...
    @abstractmethod
    def list(self, *, project_id: str | None = None, status: JobStatus | None = None, limit: int = 50) -> list[GenerationJob]: ...
