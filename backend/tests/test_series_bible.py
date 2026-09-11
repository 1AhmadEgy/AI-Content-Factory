from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.services.project_context import ProjectContextStore
from app.services.series_bible import SeriesBibleService


def test_series_bible_keeps_canonical_state_and_one_event_per_mutation():
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Kids Series"))
    bible = SeriesBibleService(ProjectContextStore(repositories.store))

    bible.initialize(
        "project-1",
        {
            "title": "يوميات أصدقاء المدرسة",
            "genre": "children_light_comedy",
            "ageRange": "6-12",
            "themes": ["daily habits", "school", "friendship"],
        },
        ["age appropriate", "light comedy", "stable character identities"],
    )
    bible.upsert_character("project-1", {"id": "ahmed", "name": "أحمد", "traits": ["curious"]})
    bible.upsert_character("project-1", {"id": "ali", "name": "علي", "traits": ["funny"]})
    bible.upsert_location("project-1", {"id": "classroom", "name": "الفصل", "rules": ["same layout"]})
    bible.record_episode("project-1", "episode-1", {"title": "النظافة في المدرسة", "sceneIds": ["scene-1"]})
    bible.record_shot("project-1", "shot-1", {"episodeId": "episode-1", "characterIds": ["ahmed", "ali"]})

    snapshot = bible.snapshot("project-1")
    assert snapshot["series"]["title"] == "يوميات أصدقاء المدرسة"
    assert snapshot["characters"]["ahmed"]["name"] == "أحمد"
    assert snapshot["locations"]["classroom"]["name"] == "الفصل"
    assert snapshot["episodes"]["episode-1"]["title"] == "النظافة في المدرسة"
    assert snapshot["latest"]["shotId"] == "shot-1"
    assert snapshot["rules"] == ["age appropriate", "light comedy", "stable character identities"]
    assert snapshot["contextVersion"] == 6

    events = bible.context.events("project-1", limit=50)
    assert len(events) == 6
    event_types = [event["eventType"] for event in reversed(events)]
    assert event_types == [
        "series.bible.initialized",
        "character.saved",
        "character.saved",
        "location.saved",
        "episode.saved",
        "shot.saved",
    ]


def test_qc_review_is_a_review_event_and_does_not_clear_latest_job():
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Kids Series"))
    bible = SeriesBibleService(ProjectContextStore(repositories.store))

    bible.record_job(
        "project-1",
        {
            "jobId": "job-qc-1",
            "type": "QC",
            "targetType": "asset",
            "targetId": "asset-1",
            "status": "SUCCEEDED",
        },
    )
    saved = bible.record_qc_review(
        "project-1",
        "review-1",
        "asset-1",
        "APPROVED",
        "2026-09-11T17:00:00+00:00",
    )

    snapshot = bible.snapshot("project-1")
    assert saved["version"] == 2
    assert snapshot["latest"]["jobId"] == "job-qc-1"
    assert snapshot["latest"]["qcId"] == "review-1"
    assert snapshot["qc"]["review-1"]["status"] == "APPROVED"
    assert snapshot["storyState"]["latestQCReview"]["reviewId"] == "review-1"

    events = bible.context.events("project-1", limit=10)
    event_types = [event["eventType"] for event in reversed(events)]
    assert event_types == ["generation.job", "qc.reviewed"]
