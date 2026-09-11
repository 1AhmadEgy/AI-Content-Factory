from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.services.project_context import ProjectContextStore
from app.services.series_bible import SeriesBibleService


def test_series_bible_keeps_canonical_state_and_event_history():
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

    events = bible.context.events("project-1", limit=50)
    event_types = {event["eventType"] for event in events}
    assert "series.bible.initialized" in event_types
    assert "character.saved" in event_types
    assert "location.saved" in event_types
    assert "episode.saved" in event_types
    assert "shot.saved" in event_types
