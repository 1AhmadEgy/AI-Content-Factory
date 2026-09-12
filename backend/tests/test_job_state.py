from app.domain.jobs import GenerationJob, JobStatus, JobType
from app.orchestrator.job_state import InvalidJobTransition, transition


def make_job() -> GenerationJob:
    return GenerationJob(id="job-1", project_id="project-1", type=JobType.SHOT, target_type="shot")


def test_valid_lifecycle_transition() -> None:
    job = make_job()
    transition(job, JobStatus.QUEUED)
    transition(job, JobStatus.RUNNING)
    transition(job, JobStatus.COMPLETED)
    assert job.status is JobStatus.COMPLETED
    assert job.progress == 1.0
    assert job.attempt == 1


def test_invalid_transition_is_rejected() -> None:
    job = make_job()
    try:
        transition(job, JobStatus.COMPLETED)
    except InvalidJobTransition:
        pass
    else:
        raise AssertionError("invalid transition was accepted")
