from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...domain.characters import CharacterProfile
from ...domain.character_repositories import CharacterRepository


class CharacterWrite(BaseModel):
    projectId: str
    name: str = Field(min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    personality: dict[str, object] = Field(default_factory=dict)
    appearance: dict[str, object] = Field(default_factory=dict)
    voice: dict[str, object] = Field(default_factory=dict)
    speakingStyle: dict[str, object] = Field(default_factory=dict)
    visualStyle: dict[str, object] = Field(default_factory=dict)
    behaviorRules: list[str] = Field(default_factory=list)
    referenceAssetIds: list[str] = Field(default_factory=list)
    providerCharacterId: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


def _data(c: CharacterProfile) -> dict[str, object]:
    return c.snapshot() | {"createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat()}


def build_router(repository: CharacterRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/characters", tags=["characters"])

    @router.post("")
    def create(body: CharacterWrite, request: Request):
        now = datetime.now(timezone.utc)
        character = CharacterProfile(id=f"char_{uuid4().hex}", project_id=body.projectId, name=body.name.strip(),
            aliases=tuple(body.aliases), description=body.description, personality=body.personality,
            appearance=body.appearance, voice=body.voice, speaking_style=body.speakingStyle,
            visual_style=body.visualStyle, behavior_rules=tuple(body.behaviorRules),
            reference_asset_ids=tuple(body.referenceAssetIds), provider_character_id=body.providerCharacterId,
            metadata=body.metadata, created_at=now, updated_at=now)
        return {"data": _data(repository.create(character)), "requestId": request.state.request_id}

    @router.get("")
    def list_characters(request: Request, projectId: str | None = None, q: str | None = None, limit: int = Query(100, ge=1, le=500)):
        items = repository.list(project_id=projectId, query=q, limit=limit)
        return {"data": [_data(c) for c in items], "meta": {"count": len(items), "limit": limit}, "requestId": request.state.request_id}

    @router.get("/{character_id}")
    def get(character_id: str, request: Request):
        character = repository.get(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="CHARACTER_NOT_FOUND")
        return {"data": _data(character), "requestId": request.state.request_id}

    @router.put("/{character_id}")
    def update(character_id: str, body: CharacterWrite, request: Request):
        current = repository.get(character_id)
        if not current:
            raise HTTPException(status_code=404, detail="CHARACTER_NOT_FOUND")
        updated = CharacterProfile(id=current.id, project_id=body.projectId, name=body.name.strip(), aliases=tuple(body.aliases),
            description=body.description, personality=body.personality, appearance=body.appearance, voice=body.voice,
            speaking_style=body.speakingStyle, visual_style=body.visualStyle, behavior_rules=tuple(body.behaviorRules),
            reference_asset_ids=tuple(body.referenceAssetIds), provider_character_id=body.providerCharacterId,
            metadata=body.metadata, version=current.version, created_at=current.created_at, updated_at=current.updated_at)
        return {"data": _data(repository.update(updated)), "requestId": request.state.request_id}

    @router.delete("/{character_id}")
    def delete(character_id: str, request: Request):
        if not repository.delete(character_id):
            raise HTTPException(status_code=404, detail="CHARACTER_NOT_FOUND")
        return {"data": {"id": character_id, "deleted": True}, "requestId": request.state.request_id}

    return router
