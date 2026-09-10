from __future__ import annotations

from typing import Any

from .country_catalog import get_country_library
from .series_templates import list_series_templates


LIBRARY_SCHEMA_VERSION = 1
LIBRARY_CATEGORIES = (
    "characters", "locations", "series_templates", "relationships", "continuity",
    "story_facts", "running_gags", "open_threads", "props", "visual_rules", "audio_rules",
    "vehicles", "workplaces", "customs", "dialects", "clothing", "architecture", "environments",
)


def build_country_library_spec(country_id: str) -> dict[str, Any] | None:
    """Return a stable empty content contract for an independent country library.

    The registry deliberately does not copy another country's characters or
    locations. Content can be seeded later without changing the API contract.
    """
    country = get_country_library(country_id)
    if country is None:
        return None
    return {
        "schemaVersion": LIBRARY_SCHEMA_VERSION,
        "countryId": country["id"],
        "libraryId": country["libraryId"],
        "name": country["name"],
        "nativeName": country["nativeName"],
        "countryCode": country["countryCode"],
        "locale": country["locale"],
        "defaultLanguage": country["defaultLanguage"],
        "dialects": list(country.get("dialects", [])),
        "status": country["status"],
        "reusable": True,
        "independent": True,
        "nonDestructive": True,
        "categories": list(LIBRARY_CATEGORIES),
        "seriesTemplates": [template["id"] for template in list_series_templates()],
        "counts": {category: 0 for category in LIBRARY_CATEGORIES},
    }


def list_country_library_specs() -> list[dict[str, Any]]:
    from .country_catalog import list_country_libraries
    return [spec for country in list_country_libraries() if (spec := build_country_library_spec(str(country["id"]))) is not None]
