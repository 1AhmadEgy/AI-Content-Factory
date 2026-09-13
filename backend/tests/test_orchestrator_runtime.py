import pytest

from app.domain.jobs import JobInput, JobType
from app.domain.projects import Project
from app.orchestrator.job_service import JobService
from app.orchestrator.runtime import OrchestratorRuntime
from app.infrastructure.sqlite import SQLiteRepositories


def test_runtime_fails_closed_when_requested_worker_is_not_registered(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Demo"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(
        project_id="project-1", job_type=JobType.IMAGE, target_type="shot",
        input=JobInput(parameters={"prompt": "hello"}, seed=7, deterministic=True),
    )
    runtime.queue.enqueue(job)

    with pytest.raises(KeyError, match="mock"):
        runtime.execute_next("mock")
