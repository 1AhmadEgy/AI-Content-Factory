from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.orchestrator.content_pipeline import ContentPipelineOrchestrator


def _job(job_type: JobType, parameters: dict, parent: str | None = None) -> GenerationJob:
    return GenerationJob(
        id=f"{job_type.value.lower()}-1",
        project_id="project-1",
        type=job_type,
        target_type="project",
        status=JobStatus.COMPLETED,
        input=JobInput(parameters=parameters, deterministic=True),
        parent_job_id=parent,
        priority=100,
        provider="mock",
        model="mock-deterministic",
    )


def test_story_completion_creates_only_scene_jobs() -> None:
    queued = []
    pipeline = ContentPipelineOrchestrator(lambda: None, queued.append)
    story = _job(JobType.STORY, {"plan": {"scenes": [{"number": 1, "shots": [{"number": 1}]}, {"number": 2, "shots": [{"number": 1}]}]}})

    # Use a tiny real service substitute with deterministic job creation.
    class Service:
        def create(self, **kwargs):
            from uuid import uuid4
            from backend.app.domain.jobs import GenerationJob
            return GenerationJob(id=str(uuid4()), project_id=kwargs["project_id"], type=kwargs["job_type"], target_type=kwargs["target_type"], target_id=kwargs["target_id"], parent_job_id=kwargs["parent_job_id"], input=kwargs["input"], priority=kwargs["priority"], provider=kwargs["provider"], model=kwargs["model"], status=JobStatus.QUEUED)
    pipeline.job_service = Service()

    created = pipeline.on_completed(story)
    assert [j.type for j in created] == [JobType.SCENE, JobType.SCENE]
    assert len(queued) == 2


def test_scene_completion_creates_shot_jobs() -> None:
    queued = []
    class Service:
        def create(self, **kwargs):
            from uuid import uuid4
            return GenerationJob(id=str(uuid4()), project_id=kwargs["project_id"], type=kwargs["job_type"], target_type=kwargs["target_type"], target_id=kwargs["target_id"], parent_job_id=kwargs["parent_job_id"], input=kwargs["input"], priority=kwargs["priority"], provider=kwargs["provider"], model=kwargs["model"], status=JobStatus.QUEUED)
    pipeline = ContentPipelineOrchestrator(Service(), queued.append)
    scene = _job(JobType.SCENE, {"scene": {"number": 1, "shots": [{"number": 1}, {"number": 2}]}})
    scene.target_id = "scene-1"

    created = pipeline.on_completed(scene)
    assert [j.type for j in created] == [JobType.SHOT, JobType.SHOT]
    assert all(j.parent_job_id == scene.id for j in created)


def test_shot_completion_creates_image_video_and_voice_jobs() -> None:
    queued = []
    class Service:
        def create(self, **kwargs):
            from uuid import uuid4
            return GenerationJob(id=str(uuid4()), project_id=kwargs["project_id"], type=kwargs["job_type"], target_type=kwargs["target_type"], target_id=kwargs["target_id"], parent_job_id=kwargs["parent_job_id"], input=kwargs["input"], priority=kwargs["priority"], provider=kwargs["provider"], model=kwargs["model"], status=JobStatus.QUEUED)
    pipeline = ContentPipelineOrchestrator(Service(), queued.append)
    shot = _job(JobType.SHOT, {"shot": {"number": 1, "prompt": "cinematic city"}, "shotNumber": 1})

    created = pipeline.on_completed(shot)
    assert [j.type for j in created] == [JobType.IMAGE, JobType.VIDEO, JobType.TTS]
    assert len(queued) == 3
