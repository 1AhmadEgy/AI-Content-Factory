from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.orchestrator.content_pipeline import ContentPipelineOrchestrator


def _job(job_type: JobType, parameters: dict, parent: str | None = None) -> GenerationJob:
    return GenerationJob(id=f"{job_type.value.lower()}-1", project_id="project-1", type=job_type, target_type="project", status=JobStatus.COMPLETED, input=JobInput(parameters=parameters, deterministic=False), parent_job_id=parent, priority=100, provider=None, model=None)


class Service:
    def create(self, **kwargs):
        from uuid import uuid4
        return GenerationJob(id=str(uuid4()), project_id=kwargs["project_id"], type=kwargs["job_type"], target_type=kwargs["target_type"], target_id=kwargs["target_id"], parent_job_id=kwargs["parent_job_id"], input=kwargs["input"], priority=kwargs["priority"], provider=kwargs["provider"], model=kwargs["model"], status=JobStatus.QUEUED)


def test_story_completion_creates_scene_jobs_and_preserves_continuity_context() -> None:
    queued = []
    pipeline = ContentPipelineOrchestrator(Service(), queued.append)
    story = _job(JobType.STORY, {"plan": {"scenes": [{"number": 1, "shots": [{"number": 1}]}]}, "topic": "test", "language": "ar", "durationSeconds": 60, "style": "documentary", "audience": "general", "platform": "youtube", "aspectRatio": "16:9", "characterIds": ["person-1"], "locationIds": ["place-1"], "continuityRules": ["same-person", "same-place"], "countryId": "libya", "libraryId": "local-library-libya", "dialect": "libyan", "productionContext": {"project": "local", "episode": "ep-1"}})
    created = pipeline.on_completed(story)
    assert [j.type for j in created] == [JobType.SCENE]
    assert created[0].input.parameters["brief"]["characterIds"] == ["person-1"]
    assert created[0].input.parameters["brief"]["locationIds"] == ["place-1"]
    assert created[0].input.parameters["brief"]["countryId"] == "libya"
    assert created[0].input.parameters["brief"]["libraryId"] == "local-library-libya"
    assert created[0].input.parameters["brief"]["continuityRules"] == ["same-person", "same-place"]


def test_scene_completion_creates_shot_and_auxiliary_audio_jobs() -> None:
    queued = []
    pipeline = ContentPipelineOrchestrator(Service(), queued.append)
    scene = _job(JobType.SCENE, {"scene": {"number": 1, "shots": [{"number": 1}, {"number": 2}]}, "brief": {"topic": "test", "language": "ar", "durationSeconds": 60, "style": "documentary", "audience": "general", "platform": "youtube", "aspectRatio": "16:9", "characterIds": ["person-1"], "locationIds": ["place-1"], "countryId": "libya", "libraryId": "local-library-libya"}})
    scene.target_id = "scene-1"
    created = pipeline.on_completed(scene)
    assert [j.type for j in created] == [JobType.SHOT, JobType.SHOT, JobType.TTS, JobType.MUSIC, JobType.SFX]
    assert all(j.parent_job_id == scene.id for j in created)


def test_shot_completion_creates_real_media_generation_jobs_and_preserves_identity() -> None:
    queued = []
    pipeline = ContentPipelineOrchestrator(Service(), queued.append)
    shot = _job(JobType.SHOT, {"shot": {"number": 1, "prompt": "cinematic city", "characterIds": ["person-1"], "locationIds": ["place-1"]}, "scene": {"number": 1, "durationSeconds": 5, "visual": "city", "narration": "city"}, "brief": {"topic": "test", "language": "ar", "durationSeconds": 60, "style": "documentary", "audience": "general", "platform": "youtube", "aspectRatio": "16:9", "characterIds": ["person-1"], "locationIds": ["place-1"], "continuityRules": ["same-person", "same-place"], "countryId": "libya", "libraryId": "local-library-libya"}, "shotNumber": 1, "takeCount": 1})
    created = pipeline.on_completed(shot)
    assert [j.type for j in created] == [JobType.IMAGE, JobType.VIDEO]
    assert len(queued) == 2
    for generation in created:
        spec = generation.input.parameters["generationSpec"]
        assert spec["parameters"]["character_ids"] == ["person-1"]
        assert spec["parameters"]["location_ids"] == ["place-1"]
        assert spec["parameters"]["country_id"] == "libya"
        assert spec["parameters"]["library_id"] == "local-library-libya"
