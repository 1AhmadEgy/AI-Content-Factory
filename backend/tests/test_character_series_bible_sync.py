from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.domain.characters import CharacterProfile
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.orchestrator.runtime import OrchestratorRuntime


def test_character_lifecycle_can_be_materialized_in_series_bible() -> None:
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Kids Series"))
    runtime = OrchestratorRuntime(repositories)

    character = CharacterProfile(
        id="char-ahmed",
        project_id="project-1",
        name="Ahmed",
        aliases=("Ahmad",),
        description="A cheerful school friend",
        personality={"traits": ["curious", "kind"]},
        appearance={"age": 9, "hair": "black"},
        voice={},
        speaking_style={"tone": "friendly"},
        visual_style={"schoolUniform": "blue"},
        behavior_rules=("age appropriate",),
        reference_asset_ids=(),
        provider_character_id=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    saved = runtime.characters.create(character)
    runtime.series_bible.upsert_character(saved.project_id, saved.snapshot())

    bible = runtime.context_snapshot("project-1")
    assert bible["characters"]["char-ahmed"]["name"] == "Ahmed"
    assert bible["characters"]["char-ahmed"]["appearance"]["age"] == 9


def test_context_schema_is_sqlite_compatible() -> None:
    repositories = SQLiteRepositories(":memory:")
    tables = {row[0] for row in repositories.store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "project_contexts" in tables
    assert "project_context_events" in tables
