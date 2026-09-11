from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...domain.content import ContentBrief
from ...orchestrator.runtime import OrchestratorRuntime


class EpisodePlanRequest(BaseModel):
    projectId: str
    idea: str = Field(min_length=1, max_length=10000)
    characterIds: list[str] = Field(default_factory=list)
    locationIds: list[str] = Field(default_factory=list)
    language: str = "ar"
    durationSeconds: int = Field(default=60, ge=5, le=3600)
    style: str = "cinematic"
    audience: str = "general"
    platform: str = "youtube"
    aspectRatio: str = "16:9"
    countryId: str = "egypt"
    libraryId: str = "local-library-egypt"
    dialect: str | None = None
    modelId: str | None = None


def build_router(runtime: OrchestratorRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/episodes", tags=["episodes"])

    @router.post("/plan")
    def plan_episode(body: EpisodePlanRequest, request: Request):
        if runtime.repositories.projects.get(body.projectId) is None:
            raise HTTPException(404, "PROJECT_NOT_FOUND")
        brief = ContentBrief(
            topic=body.idea,
            language=body.language,
            duration_seconds=body.durationSeconds,
            style=body.style,
            audience=body.audience,
            platform=body.platform,
            aspect_ratio=body.aspectRatio,
            character_ids=tuple(body.characterIds),
            location_ids=tuple(body.locationIds),
            country_id=body.countryId,
            library_id=body.libraryId,
            dialect=body.dialect,
            project_id=body.projectId,
        )
        try:
            plan = runtime.plan_content(brief, body.modelId)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "data": {
                "title": plan.title,
                "logline": plan.logline,
                "synopsis": plan.synopsis,
                "scenes": [
                    {
                        "number": scene.number,
                        "title": scene.title,
                        "durationSeconds": scene.duration_seconds,
                        "visual": scene.visual,
                        "narration": scene.narration,
                        "shots": [
                            {
                                "number": shot.number,
                                "prompt": shot.prompt,
                                "durationSeconds": shot.duration_seconds,
                                "camera": shot.camera,
                                "lighting": shot.lighting,
                                "style": shot.style,
                                "characterIds": list(shot.character_ids),
                                "locationIds": list(shot.location_ids),
                            }
                            for shot in scene.shots
                        ],
                    }
                    for scene in plan.scenes
                ],
            },
            "requestId": request.state.request_id,
        }

    return router
