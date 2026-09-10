from abc import ABC, abstractmethod
from .jobs import GenerationJob, JobStatus
from .projects import Episode, Project, Scene, Shot


class ProjectRepository(ABC):
    @abstractmethod
    def create(self, project: Project) -> Project: ...

    @abstractmethod
    def get(self, project_id: str) -> Project | None: ...

    @abstractmethod
    def list(self, limit: int, offset: int) -> tuple[list[Project], int]: ...

    @abstractmethod
    def update(self, project: Project) -> Project: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...


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

    def update_if_current(self, job: GenerationJob, expected_status: JobStatus, expected_attempt: int) -> GenerationJob:
        """Persist only if this execution still owns the expected job attempt.

        Concrete stores should override this with an atomic compare-and-update.
        The fallback keeps lightweight in-memory test repositories compatible.
        """
        current = self.get(job.id)
        if current is None:
            raise RuntimeError("JOB_NOT_FOUND")
        if current.status is not expected_status or current.attempt != expected_attempt:
            raise RuntimeError("JOB_STATE_CONFLICT")
        return self.update(job)
