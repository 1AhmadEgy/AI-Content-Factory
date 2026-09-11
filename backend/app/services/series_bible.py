from __future__ import annotations

from copy import deepcopy
from typing import Any

from .project_context import ProjectContextStore


class SeriesBibleService:
    """Canonical continuity state backed by durable project context.

    Every mutation creates exactly one materialized-context version and one
    append-only event. The bible is deliberately structured so generation
    systems can consume stable character/location/story state without relying
    on an unstructured last-event field.
    """

    def __init__(self, context: ProjectContextStore) -> None:
        self.context = context

    def snapshot(self, project_id: str) -> dict[str, Any]:
        current = self.context.get(project_id)
        bible = deepcopy(current.get("context") or {})
        for key, default in {
            "series": {}, "world": {}, "rules": [], "characters": {},
            "locations": {}, "recurringProps": {}, "relationships": {},
            "storyState": {}, "episodes": {}, "scenes": {}, "shots": {},
            "assets": {}, "qc": {}, "timeline": {}, "rendering": {},
            "publishing": {}, "continuity": {}, "latest": {},
        }.items():
            bible.setdefault(key, default)
        bible["contextVersion"] = current.get("version", 0)
        return bible

    def _save(self, project_id: str, bible: dict[str, Any], event_type: str, payload: dict[str, Any], entity_type: str | None = None, entity_id: str | None = None) -> dict[str, Any]:
        return self.context.save(project_id, bible, event_type=event_type, entity_type=entity_type, entity_id=entity_id, event_payload=payload)

    def initialize(self, project_id: str, series: dict[str, Any], rules: list[str] | None = None) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["series"] = {**bible["series"], **series}
        if rules:
            bible["rules"] = list(dict.fromkeys([*bible["rules"], *rules]))
        bible["latest"]["seriesId"] = project_id
        return self._save(project_id, bible, "series.bible.initialized", {"series": series, "rules": rules or []}, "series", project_id)

    def upsert_character(self, project_id: str, character: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        cid = str(character["id"])
        bible["characters"][cid] = {**bible["characters"].get(cid, {}), **deepcopy(character)}
        bible["latest"]["characterId"] = cid
        return self._save(project_id, bible, "character.saved", character, "character", cid)

    def upsert_location(self, project_id: str, location: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        lid = str(location["id"])
        bible["locations"][lid] = {**bible["locations"].get(lid, {}), **deepcopy(location)}
        bible["latest"]["locationId"] = lid
        return self._save(project_id, bible, "location.saved", location, "location", lid)

    def record_episode(self, project_id: str, episode_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["episodes"][episode_id] = {**bible["episodes"].get(episode_id, {}), **deepcopy(data)}
        bible["latest"]["episodeId"] = episode_id
        return self._save(project_id, bible, "episode.saved", data, "episode", episode_id)

    def record_scene(self, project_id: str, scene_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["scenes"][scene_id] = {**bible["scenes"].get(scene_id, {}), **deepcopy(data)}
        bible["latest"]["sceneId"] = scene_id
        return self._save(project_id, bible, "scene.saved", data, "scene", scene_id)

    def record_shot(self, project_id: str, shot_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["shots"][shot_id] = {**bible["shots"].get(shot_id, {}), **deepcopy(data)}
        bible["storyState"]["latestShot"] = {"id": shot_id, **deepcopy(data)}
        bible["latest"]["shotId"] = shot_id
        return self._save(project_id, bible, "shot.saved", data, "shot", shot_id)

    def record_asset(self, project_id: str, asset_id: str, data: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["assets"][asset_id] = {**bible["assets"].get(asset_id, {}), **deepcopy(data)}
        bible["latest"]["assetId"] = asset_id
        return self._save(project_id, bible, "asset.saved", data, "asset", asset_id)

    def record_qc_review(self, project_id: str, review_id: str, asset_id: str, status: str, reviewed_at: str, reason: str | None = None) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        review = {"reviewId": review_id, "assetId": asset_id, "status": status, "reviewedAt": reviewed_at}
        if reason is not None:
            review["reason"] = reason
        bible["qc"][review_id] = deepcopy(review)
        bible["storyState"]["latestQCReview"] = deepcopy(review)
        bible["latest"]["qcId"] = review_id
        return self._save(project_id, bible, "qc.reviewed", review, "qc_review", review_id)

    def record_job(self, project_id: str, job: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["storyState"]["latestJob"] = deepcopy(job)
        bible["latest"]["jobId"] = job.get("jobId")
        job_type = str(job.get("type", "")).upper()
        target_id = job.get("targetId")
        if job_type == "QC" and target_id:
            bible["qc"][str(target_id)] = deepcopy(job)
            bible["latest"]["qcId"] = str(target_id)
        elif job_type == "TIMELINE" and target_id:
            bible["timeline"][str(target_id)] = deepcopy(job)
            bible["latest"]["timelineId"] = str(target_id)
        elif job_type == "RENDER" and target_id:
            bible["rendering"][str(target_id)] = deepcopy(job)
            bible["latest"]["renderJobId"] = str(job.get("jobId") or target_id)
        elif job_type == "PUBLISH" and target_id:
            bible["publishing"][str(target_id)] = deepcopy(job)
            bible["latest"]["publishedAssetId"] = str(target_id)
        return self._save(project_id, bible, "generation.job", job, "job", job.get("jobId"))

    def update_continuity(self, project_id: str, continuity: dict[str, Any]) -> dict[str, Any]:
        bible = self.snapshot(project_id)
        bible["continuity"] = {**bible.get("continuity", {}), **deepcopy(continuity)}
        return self._save(project_id, bible, "continuity.updated", continuity, "continuity", project_id)
