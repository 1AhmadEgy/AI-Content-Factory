from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

CONTEXT_VERSION = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_series_context(*, series_id: str, title: str, template_id: str, genre: str, character_ids: list[str] | None = None, location_ids: list[str] | None = None, country_id: str = "egypt", library_id: str | None = None, source_language: str = "ar", target_languages: list[str] | None = None, dialect: str | None = None) -> dict[str, Any]:
    """Create a durable, country-aware and multilingual continuity document."""
    now = _now()
    return {
        "contextVersion": CONTEXT_VERSION, "seriesId": series_id, "title": title,
        "templateId": template_id, "genre": genre, "createdAt": now, "updatedAt": now,
        "nextEpisodeNumber": 1, "countryId": country_id, "libraryId": library_id or f"local-library-{country_id}",
        "sourceLanguage": source_language, "targetLanguages": list(target_languages or []), "dialect": dialect,
        "translationPolicy": {"preserveSource": True, "manualOverridesWin": True, "immutableVersions": True, "preserveTerms": True},
        "glossary": {}, "translationVersions": {},
        "characters": list(character_ids or []), "locations": list(location_ids or []),
        "relationships": [], "facts": [], "runningGags": [], "openThreads": [], "importantProps": [],
        "timeline": [], "episodeSnapshots": [],
        "rules": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveEstablishedFacts": True, "neverOverwriteUserChanges": True},
    }


def append_episode_memory(context: dict[str, Any], episode: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(context); snapshot = deepcopy(episode); snapshot.setdefault("savedAt", _now())
    result.setdefault("episodeSnapshots", []).append(snapshot)
    result["nextEpisodeNumber"] = max(int(result.get("nextEpisodeNumber", 1)), int(snapshot.get("episodeNumber", 0)) + 1)
    result["updatedAt"] = _now(); return result


def merge_series_defaults(context: dict[str, Any], *, character_ids: list[str] | None = None, location_ids: list[str] | None = None, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    result = deepcopy(context); result.setdefault("characters", []); result.setdefault("locations", []); result.setdefault("rules", {})
    for value in character_ids or []:
        if value not in result["characters"]: result["characters"].append(value)
    for value in location_ids or []:
        if value not in result["locations"]: result["locations"].append(value)
    for key, value in (rules or {}).items(): result["rules"].setdefault(key, deepcopy(value))
    result["updatedAt"] = _now(); return result


def build_episode_context(context: dict[str, Any], episode_number: int) -> dict[str, Any]:
    snapshot = deepcopy(context); snapshot["episodeNumber"] = episode_number; snapshot["workingSnapshotAt"] = _now()
    snapshot["sourceContextVersion"] = context.get("contextVersion", CONTEXT_VERSION); snapshot["sourceUpdatedAt"] = context.get("updatedAt")
    return snapshot
