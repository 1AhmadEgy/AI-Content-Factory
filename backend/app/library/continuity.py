from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


CONTEXT_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_series_context(
    *,
    series_id: str,
    title: str,
    template_id: str,
    genre: str,
    character_ids: list[str] | None = None,
    location_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create a durable continuity document for an episodic series."""
    return {
        "contextVersion": CONTEXT_VERSION,
        "seriesId": series_id,
        "title": title,
        "templateId": template_id,
        "genre": genre,
        "createdAt": _now(),
        "updatedAt": _now(),
        "nextEpisodeNumber": 1,
        "characters": list(character_ids or []),
        "locations": list(location_ids or []),
        "relationships": [],
        "facts": [],
        "runningGags": [],
        "openThreads": [],
        "importantProps": [],
        "timeline": [],
        "episodeSnapshots": [],
        "rules": {
            "preserveCharacterIdentity": True,
            "preserveLocationIdentity": True,
            "preserveEstablishedFacts": True,
            "neverOverwriteUserChanges": True,
        },
    }


def append_episode_memory(context: dict[str, Any], episode: dict[str, Any]) -> dict[str, Any]:
    """Append episode memory without mutating or deleting previous history."""
    result = deepcopy(context)
    snapshot = deepcopy(episode)
    snapshot.setdefault("savedAt", _now())
    result.setdefault("episodeSnapshots", []).append(snapshot)
    result["nextEpisodeNumber"] = max(
        int(result.get("nextEpisodeNumber", 1)),
        int(snapshot.get("episodeNumber", 0)) + 1,
    )
    result["updatedAt"] = _now()
    return result


def merge_series_defaults(
    context: dict[str, Any],
    *,
    character_ids: list[str] | None = None,
    location_ids: list[str] | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add missing defaults while preserving all user-owned continuity data."""
    result = deepcopy(context)
    result.setdefault("characters", [])
    result.setdefault("locations", [])
    result.setdefault("rules", {})

    for value in character_ids or []:
        if value not in result["characters"]:
            result["characters"].append(value)
    for value in location_ids or []:
        if value not in result["locations"]:
            result["locations"].append(value)
    for key, value in (rules or {}).items():
        result["rules"].setdefault(key, deepcopy(value))

    result["updatedAt"] = _now()
    return result


def build_episode_context(context: dict[str, Any], episode_number: int) -> dict[str, Any]:
    """Build a read-only working snapshot for a new episode.

    Later edits to the series library do not rewrite this snapshot.
    """
    snapshot = deepcopy(context)
    snapshot["episodeNumber"] = episode_number
    snapshot["workingSnapshotAt"] = _now()
    snapshot["sourceContextVersion"] = context.get("contextVersion", CONTEXT_VERSION)
    snapshot["sourceUpdatedAt"] = context.get("updatedAt")
    return snapshot
