from datetime import timezone

import pytest

from app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories


def test_project_and_job_round_trip() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        project = Project(id="project-1", name="Demo")
        repositories.projects.create(project)

        job = GenerationJob(
            id="job-1",
            project_id=project.id,
            type=JobType.VIDEO,
            target_type="shot",
            status=JobStatus.QUEUED,
            priority=25,
            input=JobInput(
                parameters={"prompt": "hello"},
                reference_asset_ids=["asset-1"],
                constraints={"duration": 5},
                seed=42,
                deterministic=True,
            ),
        )
        repositories.jobs.create(job)
        restored = repositories.jobs.get(job.id)

        assert restored is not None
        assert restored.id == job.id
        assert restored.project_id == project.id
        assert restored.type is JobType.VIDEO
        assert restored.status is JobStatus.QUEUED
        assert restored.input.parameters == {"prompt": "hello"}
        assert restored.input.reference_asset_ids == ["asset-1"]
        assert restored.input.constraints == {"duration": 5}
        assert restored.input.seed == 42
        assert restored.input.deterministic is True
        assert restored.created_at.tzinfo == timezone.utc
    finally:
        repositories.close()


def test_job_update_is_durable() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        job = GenerationJob(
            id="job-1",
            project_id="project-1",
            type=JobType.IMAGE,
            target_type="shot",
        )
        repositories.jobs.create(job)

        job.status = JobStatus.RUNNING
        job.progress = 0.5
        job.attempt = 1
        repositories.jobs.update(job)

        restored = repositories.jobs.get(job.id)
        assert restored is not None
        assert restored.status is JobStatus.RUNNING
        assert restored.progress == pytest.approx(0.5)
        assert restored.attempt == 1
    finally:
        repositories.close()


def test_job_requires_existing_project() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        job = GenerationJob(
            id="job-1",
            project_id="missing",
            type=JobType.IMAGE,
            target_type="shot",
        )
        with pytest.raises(Exception):
            repositories.jobs.create(job)
    finally:
        repositories.close()
