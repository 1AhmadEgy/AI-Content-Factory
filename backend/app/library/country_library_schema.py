from __future__ import annotations

"""Country-library content contract.

This schema is intentionally data-only: every country can provide its own
characters, locations, culture, production rules and six series templates
without changing the API or another country's records.
"""

from typing import Any

LIBRARY_CATEGORIES = (
    "characters", "locations", "environments", "clothing", "dialects",
    "customs", "vehicles", "workplaces", "archetypes", "seriesTemplates",
    "relationships", "continuity", "storyFacts", "runningGags", "openThreads",
    "props", "visualRules", "audioRules",
)

SERIES_GENRES = ("comedy", "action", "drama", "mystery", "adventure", "family")


def empty_country_library(country_id: str, library_id: str, *, version: int = 1) -> dict[str, Any]:
    return {
        "countryId": country_id,
        "libraryId": library_id,
        "version": version,
        "categories": list(LIBRARY_CATEGORIES),
        "seriesTemplates": [f"{genre}-series" for genre in SERIES_GENRES],
        "characters": [],
        "locations": [],
        "environments": [],
        "clothing": [],
        "dialects": [],
        "customs": [],
        "vehicles": [],
        "workplaces": [],
        "archetypes": [],
        "relationships": [],
        "continuity": {
            "preserveCharacterIdentity": True,
            "preserveLocationIdentity": True,
            "preserveEstablishedFacts": True,
            "neverOverwriteUserChanges": True,
        },
        "storyFacts": [],
        "runningGags": [],
        "openThreads": [],
        "props": [],
        "visualRules": {},
        "audioRules": {},
    }


def validate_country_library(library: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("countryId", "libraryId", "version"):
        if key not in library:
            errors.append(f"MISSING_{key.upper()}")
    categories = set(library.get("categories", []))
    missing = [item for item in LIBRARY_CATEGORIES if item not in categories]
    if missing:
        errors.append("MISSING_CATEGORIES:" + ",".join(missing))
    templates = set(library.get("seriesTemplates", []))
    expected = {f"{genre}-series" for genre in SERIES_GENRES}
    if not expected.issubset(templates):
        errors.append("MISSING_SERIES_TEMPLATES")
    return errors
