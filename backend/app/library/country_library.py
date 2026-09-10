from __future__ import annotations

from typing import Any

from .country_catalog import get_country_library, list_country_libraries
from .default_library import default_characters, default_locations
from .egypt_expanded import expanded_characters, expanded_locations
from .egypt_common import common_characters, common_locations
from .countries.libya import characters as libya_characters
from .countries.libya import library_metadata as libya_metadata
from .countries.libya import locations as libya_locations
from .series_templates import list_series_templates

LIBRARY_SCHEMA_VERSION = 1
LIBRARY_CATEGORIES = (
    "characters", "locations", "series_templates", "relationships", "continuity",
    "story_facts", "running_gags", "open_threads", "props", "visual_rules", "audio_rules",
    "vehicles", "workplaces", "customs", "dialects", "clothing", "architecture", "environments",
)


def build_country_library_spec(country_id: str) -> dict[str, Any] | None:
    """Return a stable content contract for an independent country library."""
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


def _serialize_character(value: Any) -> dict[str, Any]:
    return {
        "id": value.id, "projectId": value.project_id, "name": value.name,
        "aliases": list(value.aliases), "description": value.description,
        "personality": value.personality, "appearance": value.appearance,
        "voice": value.voice, "speakingStyle": value.speaking_style,
        "visualStyle": value.visual_style, "behaviorRules": list(value.behavior_rules),
        "referenceAssetIds": list(value.reference_asset_ids),
        "providerCharacterId": value.provider_character_id, "metadata": value.metadata,
        "version": value.version,
    }


def _serialize_location(value: Any) -> dict[str, Any]:
    return {
        "id": value.id, "projectId": value.project_id, "name": value.name,
        "aliases": list(value.aliases), "description": value.description,
        "geography": value.geography, "architecture": value.architecture,
        "environment": value.environment, "visualStyle": value.visual_style,
        "lighting": value.lighting, "weather": value.weather,
        "timeOfDay": value.time_of_day, "props": list(value.props),
        "rules": list(value.rules), "negativeConstraints": list(value.negative_constraints),
        "referenceAssetIds": list(value.reference_asset_ids),
        "providerLocationId": value.provider_location_id, "metadata": value.metadata,
        "version": value.version,
    }


def _apply_counts(spec: dict[str, Any], *, characters: int, locations: int) -> None:
    spec["contentCounts"] = {
        "characters": characters,
        "locations": locations,
        "seriesTemplates": len(spec["seriesTemplates"]),
    }


def get_country_library_content(country_id: str) -> dict[str, Any] | None:
    """Return country content without inventing data or copying another country."""
    spec = build_country_library_spec(country_id)
    if spec is None:
        return None

    if country_id == "egypt":
        characters = [*default_characters(), *expanded_characters(), *common_characters()]
        locations = [*default_locations(), *expanded_locations(), *common_locations()]
        spec["status"] = "ready"
        spec["characters"] = [_serialize_character(item) for item in characters]
        spec["locations"] = [_serialize_location(item) for item in locations]
        _apply_counts(spec, characters=len(characters), locations=len(locations))
        spec["seedSource"] = ["default_library", "egypt_expanded", "egypt_common"]
        return spec

    if country_id == "libya":
        metadata = libya_metadata()
        characters = libya_characters()
        locations = libya_locations()
        spec.update({
            "status": metadata["status"],
            "dialectRules": metadata["dialectRules"],
            "customs": metadata["customs"],
            "vehicles": metadata["vehicles"],
            "workplaces": metadata["workplaces"],
            "archetypes": metadata["archetypes"],
            "continuity": metadata["continuity"],
            "visualRules": metadata["visualRules"],
            "audioRules": metadata["audioRules"],
            "seedSource": metadata["seedSource"],
            "characters": [_serialize_character(item) for item in characters],
            "locations": [_serialize_location(item) for item in locations],
        })
        _apply_counts(spec, characters=len(characters), locations=len(locations))
        return spec

    spec["contentCounts"] = {"characters": 0, "locations": 0, "seriesTemplates": len(spec["seriesTemplates"])}
    spec["seedSource"] = []
    return spec


def list_country_library_specs() -> list[dict[str, Any]]:
    return [
        spec for country in list_country_libraries()
        if (spec := build_country_library_spec(str(country["id"]))) is not None
    ]


def list_country_library_summaries() -> list[dict[str, Any]]:
    """Lightweight selector data with truthful content counts and readiness."""
    result: list[dict[str, Any]] = []
    for country in list_country_libraries():
        content = get_country_library_content(str(country["id"]))
        assert content is not None
        result.append({
            **country,
            "contentCounts": content["contentCounts"],
            "categories": content["categories"],
            "seriesTemplateCount": len(content["seriesTemplates"]),
        })
    return result
