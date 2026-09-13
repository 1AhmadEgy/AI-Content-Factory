from app.domain.jobs import JobInput, JobStatus, JobType
from app.domain.projects import Project
from app.orchestrator.job_service import JobService
from app.orchestrator.runtime import OrchestratorRuntime
from app.infrastructure.sqlite import SQLiteRepositories


def test_runtime_fails_closed_when_no_real_provider_is_configured(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Demo"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(
        project_id="project-1", job_type=JobType.IMAGE, target_type="shot",
        input=JobInput(parameters={"prompt": "hello"}, seed=7, deterministic=True),
    )
    runtime.queue.enqueue(job)

    result = runtime.execute_next("auto")

    assert result is not None
    assert result.job.id == job.id
    assert result.status is JobStatus.FAILED
    assert result.job.error_code == "MODEL_CAPABILITY_UNAVAILABLE"
    persisted = repositories.jobs.get(job.id)
    assert persisted is not None
    assert persisted.status is JobStatus.FAILED
