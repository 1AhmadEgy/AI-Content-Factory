import pytest

from backend.app.domain.jobs import JobInput, JobType
from backend.app.domain.projects import Project
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.runtime import OrchestratorRuntime
from backend.app.infrastructure.sqlite import SQLiteRepositories


def test_runtime_does_not_use_implicit_mock_worker(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Demo"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(project_id="project-1", job_type=JobType.IMAGE, target_type="shot", input=JobInput(parameters={"prompt": "hello"}, deterministic=False))
    runtime.queue.enqueue(job)
    with pytest.raises(KeyError):
        runtime.execute_next("mock")
