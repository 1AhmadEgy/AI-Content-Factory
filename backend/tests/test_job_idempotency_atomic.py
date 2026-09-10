from backend.app.domain.jobs import JobInput, JobType
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.orchestrator.job_service import JobService


def test_idempotency_conflict_does_not_leave_orphan_job() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        service = JobService(repositories.jobs)
        first = service.build(
            project_id="project-1",
            job_type=JobType.IMAGE,
            target_type="shot",
            input=JobInput(parameters={"prompt": "same"}),
        )
        second = service.build(
            project_id="project-1",
            job_type=JobType.IMAGE,
            target_type="shot",
            input=JobInput(parameters={"prompt": "same"}),
        )

        assert repositories.jobs.create_with_idempotency(
            first, "idem-1", "POST:/api/v1/jobs", "fingerprint-1"
        )[0] is True
        claimed, existing = repositories.jobs.create_with_idempotency(
            second, "idem-1", "POST:/api/v1/jobs", "fingerprint-1"
        )

        assert claimed is False
        assert existing is not None
        assert existing["resource_id"] == first.id
        assert repositories.jobs.get(first.id) is not None
        assert repositories.jobs.get(second.id) is None
    finally:
        repositories.close()
