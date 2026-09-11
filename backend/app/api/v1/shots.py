from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...domain.jobs import JobInput, JobType
from ...infrastructure.shot_composition_repository import SQLiteShotCompositionRepository, ShotCharacterLink
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime
from ...services.shot_composer import ShotComposer


class CharacterInShot(BaseModel):
    characterId: str
    action: str | None = None
    emotion: str | None = None
    dialogue: str | None = None
    pose: str | None = None
    expressionOverride: str | None = None
    positionOrder: int = Field(default=0, ge=0)


class ComposeShotRequest(BaseModel):
    characters: list[CharacterInShot] = Field(min_length=1)
    locationId: str | None = None
    cameraAngle: str = "medium"
    mood: str | None = None
    sceneContext: str | None = None
    durationSec: float = Field(default=3.0, gt=0, le=120)
    visualStyle: dict[str, Any] = Field(default_factory=dict)


class AttachCharactersRequest(BaseModel):
    characters: list[CharacterInShot] = Field(min_length=1)


class LocationLinkRequest(BaseModel):
    locationId: str
    timeOfDay: str | None = None
    weather: str | None = None
    atmosphere: str | None = None


class GenerateImageRequest(BaseModel):
    size: str = "1024x1024"
    quality: str | None = None
    outputFormat: str = "png"


def build_router(runtime: OrchestratorRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/shots", tags=["shots"])
    links = SQLiteShotCompositionRepository(runtime.repositories.store)
    jobs = JobService(runtime.repositories.jobs)
    composer = ShotComposer()

    def _characters(items: list[CharacterInShot]):
        result = []
        seen: set[str] = set()
        for item in items:
            if item.characterId in seen:
                raise HTTPException(400, "DUPLICATE_CHARACTER")
            seen.add(item.characterId)
            character = runtime.characters.get(item.characterId)
            if character is None:
                raise HTTPException(404, f"CHARACTER_NOT_FOUND:{item.characterId}")
            result.append((character, item))
        return result

    def _location(location_id: str | None):
        if not location_id:
            return None
        location = runtime.locations.get(location_id)
        if location is None:
            raise HTTPException(404, "LOCATION_NOT_FOUND")
        return location

    def _compose(body: ComposeShotRequest):
        selected = _characters(body.characters)
        location = _location(body.locationId)
        character_objects = [character for character, _ in selected]
        actions = {item.characterId: item.action for _, item in selected if item.action}
        emotions = {item.characterId: item.emotion for _, item in selected if item.emotion}
        style = body.visualStyle or (character_objects[0].visual_style if character_objects else {})
        result = composer.compose(character_objects, location, style, camera_angle=body.cameraAngle, mood=body.mood,
                                  scene_context=body.sceneContext, character_actions=actions, character_emotions=emotions)
        return selected, location, result, composer.continuity_hash(character_objects, location)

    @router.post("/compose")
    def compose(body: ComposeShotRequest, request: Request):
        selected, location, result, continuity = _compose(body)
        return {"data": {"prompt": result["prompt"], "negativePrompt": result["negative_prompt"], "continuityHash": continuity,
                          "characters": [{"id": c.id, "name": c.name} for c, _ in selected],
                          "location": {"id": location.id, "name": location.name} if location else None},
                "requestId": request.state.request_id}

    @router.post("/{shot_id}/compose")
    def compose_existing(shot_id: str, body: ComposeShotRequest, request: Request):
        if runtime.repositories.shots.get(shot_id) is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        selected, location, result, continuity = _compose(body)
        links.replace_characters([ShotCharacterLink(
            id=f"shotchar_{uuid.uuid4().hex}", shot_id=shot_id, character_id=character.id,
            position_order=item.positionOrder, action=item.action, emotion=item.emotion, dialogue=item.dialogue,
            pose=item.pose, expression_override=item.expressionOverride, is_speaking=bool(item.dialogue),
        ) for character, item in selected])
        if location:
            links.set_location(shot_id, location.id)
        style = body.visualStyle or (selected[0][0].visual_style if selected else {})
        links.update_generation(shot_id, prompt=result["prompt"], negative_prompt=result["negative_prompt"], status="pending", error="",
                                continuity_hash=continuity, camera_angle=body.cameraAngle, mood=body.mood, visual_style=style)
        return {"data": {"shotId": shot_id, "prompt": result["prompt"], "negativePrompt": result["negative_prompt"], "continuityHash": continuity},
                "requestId": request.state.request_id}

    @router.get("/{shot_id}")
    def get_shot(shot_id: str, request: Request):
        shot = runtime.repositories.shots.get(shot_id)
        if shot is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        row = runtime.repositories.store._get("shots", shot_id)
        image_jobs = [job for job in runtime.repositories.jobs.list(limit=200) if job.type is JobType.IMAGE and job.target_type == "shot" and job.target_id == shot_id]
        latest = image_jobs[0] if image_jobs else None
        return {"data": {
            "id": shot.id, "sceneId": shot.scene_id, "orderIndex": shot.order_index, "prompt": row["prompt"] if row else shot.prompt,
            "negativePrompt": row["generated_negative_prompt"] if row else None, "cameraAngle": row["camera_angle"] if row else "medium",
            "mood": row["mood"] if row else None, "generationStatus": row["generation_status"] if row else "pending",
            "continuityHash": row["continuity_hash"] if row else None,
            "imageAssetIds": latest.output.asset_ids if latest and latest.output else [],
            "imageJobId": latest.id if latest else None,
            "imageJobStatus": latest.status.value if latest else None,
            "characters": [{"characterId": link.character_id, "action": link.action, "emotion": link.emotion, "dialogue": link.dialogue} for link in links.list_characters(shot_id)],
        }, "requestId": request.state.request_id}

    @router.post("/{shot_id}/attach-characters")
    def attach_characters(shot_id: str, body: AttachCharactersRequest, request: Request):
        if runtime.repositories.shots.get(shot_id) is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        selected = _characters(body.characters)
        links.replace_characters([ShotCharacterLink(
            id=f"shotchar_{uuid.uuid4().hex}", shot_id=shot_id, character_id=character.id,
            position_order=item.positionOrder, action=item.action, emotion=item.emotion, dialogue=item.dialogue,
            pose=item.pose, expression_override=item.expressionOverride, is_speaking=bool(item.dialogue),
        ) for character, item in selected])
        return {"data": {"shotId": shot_id, "attached": len(selected)}, "requestId": request.state.request_id}

    @router.put("/{shot_id}/location")
    def attach_location(shot_id: str, body: LocationLinkRequest, request: Request):
        if runtime.repositories.shots.get(shot_id) is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        if runtime.locations.get(body.locationId) is None:
            raise HTTPException(404, "LOCATION_NOT_FOUND")
        links.set_location(shot_id, body.locationId, time_of_day=body.timeOfDay, weather=body.weather, atmosphere=body.atmosphere)
        return {"data": {"shotId": shot_id, "locationId": body.locationId}, "requestId": request.state.request_id}

    @router.get("/{shot_id}/characters")
    def get_characters(shot_id: str, request: Request):
        if runtime.repositories.shots.get(shot_id) is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        result = []
        for link in links.list_characters(shot_id):
            character = runtime.characters.get(link.character_id)
            if character is None:
                continue
            result.append({"id": link.id, "characterId": link.character_id, "name": character.name,
                           "action": link.action, "emotion": link.emotion, "dialogue": link.dialogue,
                           "pose": link.pose, "isSpeaking": link.is_speaking, "voiceAudioAssetId": link.voice_audio_asset_id})
        return {"data": result, "requestId": request.state.request_id}

    @router.post("/{shot_id}/generate-image", status_code=202)
    def generate_image(shot_id: str, body: GenerateImageRequest, request: Request):
        shot = runtime.repositories.shots.get(shot_id)
        if shot is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        row = runtime.repositories.store._get("shots", shot_id)
        prompt = row["prompt"] if row else ""
        if not prompt:
            raise HTTPException(400, "SHOT_PROMPT_REQUIRED")
        project_id = runtime.repositories.store.connection.execute(
            "SELECT p.id FROM projects p JOIN episodes e ON e.project_id=p.id JOIN scenes s ON s.episode_id=e.id JOIN shots sh ON sh.scene_id=s.id WHERE sh.id=?", (shot_id,)
        ).fetchone()
        if project_id is None:
            raise HTTPException(422, "SHOT_PROJECT_NOT_RESOLVED")
        model = os.getenv("AICF_IMAGE_MODEL", "gpt-image-2")
        job = jobs.create(project_id=project_id[0], job_type=JobType.IMAGE, target_type="shot", target_id=shot_id,
                          priority=50, provider="openai", model=model,
                          input=JobInput(parameters={"prompt": prompt, "size": body.size, "output_format": body.outputFormat, **({"quality": body.quality} if body.quality else {})}))
        runtime.queue.enqueue(job)
        links.update_generation(shot_id, status="queued", error="")
        return {"data": {"jobId": job.id, "shotId": shot_id, "status": job.status.value}, "requestId": request.state.request_id}

    @router.post("/{shot_id}/generate-voice", status_code=202)
    def generate_voice(shot_id: str, request: Request):
        if runtime.repositories.shots.get(shot_id) is None:
            raise HTTPException(404, "SHOT_NOT_FOUND")
        row = runtime.repositories.store.connection.execute("SELECT project_id FROM episodes e JOIN scenes s ON s.episode_id=e.id JOIN shots sh ON sh.scene_id=s.id WHERE sh.id=?", (shot_id,)).fetchone()
        if row is None:
            raise HTTPException(422, "SHOT_PROJECT_NOT_RESOLVED")
        created = []
        model = os.getenv("AICF_TTS_MODEL", "gpt-4o-mini-tts")
        for link in links.list_characters(shot_id):
            if not link.is_speaking or not link.dialogue:
                continue
            character = runtime.characters.get(link.character_id)
            if character is None:
                continue
            voice = character.voice.get("ttsVoiceId") or character.voice.get("voice") or "alloy"
            job = jobs.create(project_id=row[0], job_type=JobType.TTS, target_type="shot_character", target_id=link.id,
                              priority=60, provider="openai", model=model,
                              input=JobInput(parameters={"text": link.dialogue, "voice": voice, "response_format": "mp3", "shotId": shot_id, "characterId": character.id}))
            runtime.queue.enqueue(job)
            created.append({"jobId": job.id, "characterId": character.id, "dialogue": link.dialogue})
        if not created:
            raise HTTPException(400, "NO_SPEAKING_CHARACTERS")
        return {"data": {"shotId": shot_id, "jobs": created}, "requestId": request.state.request_id}

    return router
