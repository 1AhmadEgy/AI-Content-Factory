from app.domain.character_consistency import ReferenceStatus
from app.domain.projects import Project
from app.domain.storyboard import CameraAngle, Shot, ShotType
from app.infrastructure.sqlite import SQLiteRepositories
from app.services.character_consistency import CharacterConsistencyError, CharacterConsistencyService
from app.services.project_context import ProjectContextStore
from app.services.series_bible import SeriesBibleService


def make_service():
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Test"))
    bible = SeriesBibleService(ProjectContextStore(repositories.store))
    return CharacterConsistencyService(bible), bible


def test_master_reference_is_explicitly_approved_and_persisted():
    service, bible = make_service()
    candidate = service.register_reference(
        "project-1",
        character_id="ahmed",
        asset_id="asset-ref-1",
        embedding=(1.0, 0.0),
        provenance={"provider_id": "real-image-provider", "provider_run_id": "run-1"},
    )
    assert candidate.status is ReferenceStatus.CANDIDATE
    assert service.master_reference("project-1", "ahmed") is None

    approved = service.approve_master_reference("project-1", candidate)
    master = service.master_reference("project-1", "ahmed")
    assert approved.status is ReferenceStatus.APPROVED
    assert master is not None
    assert master.asset_id == "asset-ref-1"
    assert bible.snapshot("project-1")["continuity"]["masterReferences"]["ahmed"] == candidate.reference_id


def test_anchor_shot_requires_approved_master_reference():
    service, _ = make_service()
    shot = Shot(
        shot_id="shot-1",
        scene_id="scene-1",
        shot_type=ShotType.MEDIUM,
        camera_angle=CameraAngle.EYE_LEVEL,
        prompt="Ahmed walks into the classroom.",
        duration_seconds=4.0,
        character_ids=("ahmed",),
    )
    try:
        service.anchor_shot("project-1", shot)
        assert False, "expected missing master reference error"
    except CharacterConsistencyError as exc:
        assert "approved master reference" in str(exc)


def test_similarity_qc_is_deterministic_and_thresholded():
    service, _ = make_service()
    reference = service.register_reference(
        "project-1", character_id="ahmed", asset_id="asset-ref", embedding=(1.0, 0.0)
    )
    reference = service.approve_master_reference("project-1", reference)
    result = service.check_similarity(
        reference,
        candidate_asset_id="asset-shot",
        candidate_embedding=(1.0, 0.0),
        threshold=0.9,
    )
    assert result.score == 1.0
    assert result.passed is True

    failed = service.check_similarity(
        reference,
        candidate_asset_id="asset-shot-2",
        candidate_embedding=(-1.0, 0.0),
        threshold=0.9,
    )
    assert failed.score == 0.0
    assert failed.passed is False


def test_similarity_without_embedding_provider_fails_truthfully():
    service, _ = make_service()
    reference = service.register_reference(
        "project-1", character_id="ahmed", asset_id="asset-ref"
    )
    reference = service.approve_master_reference("project-1", reference)
    try:
        service.check_similarity(reference, candidate_asset_id="asset-shot")
        assert False, "expected missing embedding error"
    except CharacterConsistencyError as exc:
        assert "embedding" in str(exc)
