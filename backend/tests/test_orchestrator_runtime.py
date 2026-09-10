from backend.app.domain.jobs import JobInput, JobType
from backend.app.domain.projects import Project
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.runtime import OrchestratorRuntime
from backend.app.infrastructure.sqlite import SQLiteRepositories


def test_runtime_executes_queued_job_and_persists_events(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Demo"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(project_id="project-1", job_type=JobType.IMAGE, target_type="shot", input=JobInput(parameters={"prompt": "hello"}, seed=7, deterministic=True))
    runtime.queue.enqueue(job)
    result = runtime.execute_next("mock")
    assert result is not None and result.job.id == job.id and result.status.value == "COMPLETED"
    persisted = repositories.jobs.get(job.id)
    assert persisted is not None and persisted.output is not None and persisted.output.asset_ids
    events = runtime.events.list_for_job(job.id)
    assert [event.event_type for event in events] == ["JOB_STARTED", "JOB_COMPLETED"]
