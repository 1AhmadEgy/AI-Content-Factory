from __future__ import annotations

import os
from datetime import datetime, timezone

from ..domain.projects import Project
from ..infrastructure.character_repository import SQLiteCharacterRepository
from ..infrastructure.location_repository import SQLiteLocationRepository
from .country_catalog import list_country_libraries
from .default_library import DEFAULT_LIBRARY_PROJECT_ID, default_characters, default_locations
from .egypt_catalog import EGYPT_LIBRARY_CATEGORIES, EGYPT_LIBRARY_NAME, EGYPT_LIBRARY_VERSION, EGYPT_SERIES_TEMPLATE_IDS
from .egypt_expanded import expanded_characters, expanded_locations
from .egypt_common import common_characters, common_locations
from .countries.libya import LIBRARY_PROJECT_ID as LIBYA_LIBRARY_PROJECT_ID
from .countries.libya import characters as libya_characters
from .countries.libya import locations as libya_locations


def ensure_country_library_projects(repositories) -> dict[str, int]:
    """Create independent metadata projects for every registered country additively."""
    if os.getenv("AICF_SEED_COUNTRY_LIBRARIES", "true").strip().lower() in {"0", "false", "no", "off"}:
        return {"created": 0}
    created = 0
    now = datetime.now(timezone.utc)
    for country in list_country_libraries():
        project_id = str(country["libraryId"])
        if repositories.projects.get(project_id) is not None:
            continue
        repositories.projects.create(Project(
            id=project_id,
            name=str(country["name"]),
            description=f"{country['name']} reusable content library. Content is isolated from every other country library.",
            settings={
                "kind": "reusable-library",
                "libraryName": country["name"],
                "country": country["name"],
                "countryId": country["id"],
                "countryCode": country["countryCode"],
                "libraryId": project_id,
                "libraryVersion": country.get("libraryVersion", 1),
                "status": country.get("status", "catalog-only"),
                "defaultLanguage": country["defaultLanguage"],
                "locale": country["locale"],
                "dialects": list(country.get("dialects", [])),
                "supportedLanguages": list(country.get("supportedLanguages", [])),
                "nonDestructive": True,
            },
            created_at=now,
            updated_at=now,
        ))
        created += 1
    return {"created": created}


def _seed_reusable_records(repositories, project_id: str, characters, locations) -> dict[str, int]:
    """Seed reusable records with bounded database round-trips.

    The old implementation performed one SELECT for every catalog item on every
    startup. Library catalogs are static, so load each project's IDs once and
    only issue INSERTs for genuinely missing records.
    """
    character_repo = SQLiteCharacterRepository(repositories.store)
    location_repo = SQLiteLocationRepository(repositories.store)
    existing_character_ids = {item.id for item in character_repo.list(project_id=project_id, limit=500)}
    existing_location_ids = {item.id for item in location_repo.list(project_id=project_id, limit=500)}
    added_characters = 0
    added_locations = 0
    for item in characters:
        if item.project_id == project_id and item.id not in existing_character_ids:
            character_repo.create(item)
            existing_character_ids.add(item.id)
            added_characters += 1
    for item in locations:
        if item.project_id == project_id and item.id not in existing_location_ids:
            location_repo.create(item)
            existing_location_ids.add(item.id)
            added_locations += 1
    return {"characters": added_characters, "locations": added_locations}


def ensure_libya_library(repositories) -> dict[str, int]:
    """Seed the curated Libya starter pack additively; never overwrite user records."""
    if os.getenv("AICF_SEED_LIBYA_LIBRARY", "true").strip().lower() in {"0", "false", "no", "off"}:
        return {"characters": 0, "locations": 0}
    ensure_country_library_projects(repositories)
    return _seed_reusable_records(
        repositories,
        LIBYA_LIBRARY_PROJECT_ID,
        libya_characters(),
        libya_locations(),
    )


def ensure_egypt_library(repositories) -> dict[str, int]:
    """Seed the reusable Egypt library additively; never overwrite user-owned records."""
    if os.getenv("AICF_SEED_DEFAULT_LIBRARY", "true").strip().lower() in {"0", "false", "no", "off"}:
        return {"characters": 0, "locations": 0}

    ensure_country_library_projects(repositories)
    project = repositories.projects.get(DEFAULT_LIBRARY_PROJECT_ID)
    if project is None:
        now = datetime.now(timezone.utc)
        repositories.projects.create(Project(
            id=DEFAULT_LIBRARY_PROJECT_ID,
            name=EGYPT_LIBRARY_NAME,
            description="Egypt reusable library: characters, locations, series templates, and production-ready continuity defaults.",
            settings={
                "kind": "reusable-library",
                "libraryName": EGYPT_LIBRARY_NAME,
                "country": "Egypt",
                "countryId": "egypt",
                "libraryVersion": EGYPT_LIBRARY_VERSION,
                "seedVersion": 5,
                "categories": list(EGYPT_LIBRARY_CATEGORIES),
                "seriesTemplates": list(EGYPT_SERIES_TEMPLATE_IDS),
                "nonDestructive": True,
            },
            created_at=now,
            updated_at=now,
        ))

    character_items = [*default_characters(), *expanded_characters(), *common_characters()]
    location_items = [*default_locations(), *expanded_locations(), *common_locations()]
    return _seed_reusable_records(
        repositories,
        DEFAULT_LIBRARY_PROJECT_ID,
        character_items,
        location_items,
    )
