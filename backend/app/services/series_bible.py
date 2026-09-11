from __future__ import annotations

from copy import deepcopy
from typing import Any

from .project_context import ProjectContextStore


class SeriesBibleService:
    """Structured continuity layer backed by the durable project context store.

    The bible is materialized in ``context_json`` while the context store keeps
    an append-only event history. Every mutation therefore has both a current
    canonical state and an auditable history.
    """

    def __init__(self, context: ProjectContextStore) -> None:
        self.context = context

    def snapshot(self, project_id: str) -> dict[str, Any]:
        current = self.context.get(project_id)
        bible = deepcopy(current.get("context") or {})
        bible.setdefault("series", {})
        bible.setdefault("world", {})
        bible.setdefault("rules", [])
        bible.setdefault("characters", {})
        bible.setdefault("locations", {})
        bible.setdefault("recurringProps", {})
        bible.setdefault("relationships", {})
        bible.setdefault("storyState", {})
        bible.setdefault("episodes", {})
        bible.setdefault("continuity", {})
        bible.setdefault("latest", {})
        bible["contextVersion"] = current.get("version", 0)
        return bible

    def initialize(self, project_id: str, series: dict[str, Any], rules: list[str] | None = None) -> dict[str, Any]:
        current = self.snapshot(project_id)
        current["series"] = {**current.get("series", {}), **series}
        if rules:
            current["rules"] = list(dict.fromkeys([*current.get("rules", []), *rules]))
        saved = self.context.save(project_id, current)
        self.context.append_event(project_id, "series.bible.initialized", {"series": series, "rules": rules or []}, entity_type="series", entity_id=project_id)
        return saved

    def upsert_character(self, project_id: str, character: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        character_id = str(character["id"])
        previous = bible["characters"].get(character_id, {})
        bible["characters"][character_id] = {**previous, **character}
        bible["latest"]["characterId"] = character_id
        saved = self.context.save(project_id, bible)
        self.context.append_event(project_id, "character.saved", character, entity_type="character", entity_id=character_id)
        return saved

    def upsert_location(self, project_id: str, location: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        location_id = str(location["id"])
        previous = bible["locations"].get(location_id, {})
        bible["locations"][location_id] = {**previous, **location}
        bible["latest"]["locationId"] = location_id
        saved = self.context.save(project_id, bible)
        self.context.append_event(project_id, "location.saved", location, entity_type="location", entity_id=location_id)
        return saved

    def record_episode(self, project_id: str, episode_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        previous = bible["episodes"].get(episode_id, {})
        bible["episodes"][episode_id] = {**previous, **data}
        bible["latest"]["episodeId"] = episode_id
        saved = self.context.save(project_id, bible)
        self.context.append_event(project_id, "episode.saved", data, entity_type="episode", entity_id=episode_id)
        return saved

    def record_shot(self, project_id: str, shot_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["storyState"]["latestShot"] = {"id": shot_id, **data}
        bible["latest"]["shotId"] = shot_id
        saved = self.context.save(project_id, bible)
        self.context.append_event(project_id, "shot.saved", data, entity_type="shot", entity_id=shot_id)
        return saved

    def record_job(self, project_id: str, job: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["storyState"]["latestJob"] = job
        bible["latest"]["jobId"] = job.get("jobId")
        saved = self.context.save(project_id, bible)
        self.context.append_event(project_id, "generation.job", job, entity_type="job", entity_id=job.get("jobId"))
        return saved

    def update_continuity(self, project_id: str, continuity: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["continuity"] = {**bible.get("continuity", {}), **continuity}
        return self.context.save(project_id, bible)
