from __future__ import annotations

import os
from datetime import datetime, timezone

from ..domain.projects import Project
from ..infrastructure.character_repository import SQLiteCharacterRepository
from ..infrastructure.location_repository import SQLiteLocationRepository
from .default_library import DEFAULT_LIBRARY_PROJECT_ID, default_characters, default_locations
from .egypt_expanded import expanded_characters, expanded_locations


def ensure_egypt_library(repositories) -> dict[str, int]:
    """Seed built-ins once, without overwriting user edits or deleting local data."""
    if os.getenv("AICF_SEED_DEFAULT_LIBRARY", "true").strip().lower() in {"0", "false", "no", "off"}:
        return {"characters": 0, "locations": 0}

    project = repositories.projects.get(DEFAULT_LIBRARY_PROJECT_ID)
    if project is None:
        now = datetime.now(timezone.utc)
        repositories.projects.create(Project(
            id=DEFAULT_LIBRARY_PROJECT_ID,
            name="مكتبة مصر المحلية",
            description="مكتبة محلية قابلة لإعادة الاستخدام للشخصيات والمواقع والقوالب الجاهزة.",
            settings={"kind":"reusable-library","country":"Egypt","seedVersion":2},
            created_at=now,
            updated_at=now,
        ))

    characters = SQLiteCharacterRepository(repositories.store)
    locations = SQLiteLocationRepository(repositories.store)
    added_characters = 0
    added_locations = 0

    # Existing records are deliberately left untouched. This is the key persistence rule.
    for item in [*default_characters(), *expanded_characters()]:
        if item.project_id != DEFAULT_LIBRARY_PROJECT_ID:
            continue
        if characters.get(item.id) is None:
            characters.create(item)
            added_characters += 1

    for item in [*default_locations(), *expanded_locations()]:
        if item.project_id != DEFAULT_LIBRARY_PROJECT_ID:
            continue
        if locations.get(item.id) is None:
            locations.create(item)
            added_locations += 1

    return {"characters": added_characters, "locations": added_locations}
