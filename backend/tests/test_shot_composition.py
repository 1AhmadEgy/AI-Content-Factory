from __future__ import annotations

from datetime import datetime, timezone

from app.domain.characters import CharacterProfile
from app.domain.locations import LocationProfile
from app.infrastructure.character_repository import SQLiteCharacterRepository
from app.infrastructure.location_repository import SQLiteLocationRepository
from app.infrastructure.shot_composition_repository import SQLiteShotCompositionRepository, ShotCharacterLink
from app.infrastructure.sqlite import SQLiteStore
from app.services.shot_composer import ShotComposer


def _character(cid: str, name: str) -> CharacterProfile:
    now = datetime.now(timezone.utc)
    return CharacterProfile(
        id=cid,
        project_id="project-1",
        name=name,
        description="young fighter",
        appearance={"hairColor": "black", "eyeColor": "brown", "outfit": "training clothes"},
        personality={"trait": "determined"},
        visual_style={"style": "anime cinematic"},
        created_at=now,
        updated_at=now,
    )


def test_shot_composer_is_deterministic():
    character = _character("char-1", "Ziko")
    location = LocationProfile(id="loc-1", project_id="project-1", name="Dojo", description="old wooden dojo")
    composer = ShotComposer()

    first = composer.compose([character], location, camera_angle="close_up", mood="epic", character_emotions={"char-1": "determined"})
    second = composer.compose([character], location, camera_angle="close_up", mood="epic", character_emotions={"char-1": "determined"})

    assert first == second
    assert "Ziko" in first["prompt"]
    assert "old wooden dojo" in first["prompt"]
    assert "low quality" in first["negative_prompt"]
    assert composer.continuity_hash([character], location) == composer.continuity_hash([character], location)


def test_shot_links_persist_and_are_replaced():
    store = SQLiteStore(":memory:")
    now = datetime.now(timezone.utc).isoformat()
    store._insert("INSERT INTO projects(id,name,description,settings_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("project-1", "P", "", "{}", now, now))
    store._insert("INSERT INTO episodes(id,project_id,title,created_at,updated_at) VALUES(?,?,?,?,?)", ("ep-1", "project-1", "E", now, now))
    store._insert("INSERT INTO scenes(id,episode_id,title,order_index,created_at) VALUES(?,?,?,?,?)", ("scene-1", "ep-1", "S", 0, now))
    store._insert("INSERT INTO shots(id,scene_id,order_index,prompt,created_at) VALUES(?,?,?,?,?)", ("shot-1", "scene-1", 0, "", now))

    SQLiteCharacterRepository(store).create(_character("char-1", "Ziko"))
    SQLiteLocationRepository(store).create(LocationProfile(id="loc-1", project_id="project-1", name="Dojo"))
    repo = SQLiteShotCompositionRepository(store)

    repo.replace_characters([ShotCharacterLink(id="link-1", shot_id="shot-1", character_id="char-1", action="runs", is_speaking=True)])
    assert len(repo.list_characters("shot-1")) == 1
    assert repo.list_characters("shot-1")[0].action == "runs"

    repo.replace_characters([ShotCharacterLink(id="link-2", shot_id="shot-1", character_id="char-1", action="fights")])
    links = repo.list_characters("shot-1")
    assert len(links) == 1
    assert links[0].action == "fights"

    repo.set_location("shot-1", "loc-1", weather="clear")
    assert repo.get_location("shot-1")["location_id"] == "loc-1"

    repo.update_generation("shot-1", prompt="real prompt", negative_prompt="bad", status="queued", continuity_hash="abc")
    row = store._get("shots", "shot-1")
    assert row["prompt"] == "real prompt"
    assert row["generated_negative_prompt"] == "bad"
    assert row["generation_status"] == "queued"
    assert row["continuity_hash"] == "abc"
