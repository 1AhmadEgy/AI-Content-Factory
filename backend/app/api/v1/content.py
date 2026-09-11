from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ...domain.characters import CharacterProfile
from ...domain.locations import LocationProfile
from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime

RESOURCE_TYPES={"series","episode","story","character","world","location","scene","shot","dialogue","voice","timeline"}
JOB_TYPES={"story":JobType.STORY,"character":JobType.CHARACTER,"world":JobType.WORLD,"scene":JobType.SCENE,"shot":JobType.SHOT,"dialogue":JobType.TTS,"voice":JobType.TTS,"timeline":JobType.TIMELINE}
class ResourceRequest(BaseModel):
    projectId:str|None=None; parentId:str|None=None; title:str=Field(default="Untitled",min_length=1,max_length=500); description:str=Field(default="",max_length=10000); data:dict[str,Any]=Field(default_factory=dict)
class PatchResourceRequest(BaseModel):
    title:str|None=Field(default=None,min_length=1,max_length=500); description:str|None=Field(default=None,max_length=10000); data:dict[str,Any]|None=None; parentId:str|None=None
class CharacterWrite(BaseModel):
    projectId:str; name:str=Field(min_length=1,max_length=200); aliases:list[str]=Field(default_factory=list); description:str=""
    personality:dict[str,object]=Field(default_factory=dict); appearance:dict[str,object]=Field(default_factory=dict); voice:dict[str,object]=Field(default_factory=dict); speakingStyle:dict[str,object]=Field(default_factory=dict); visualStyle:dict[str,object]=Field(default_factory=dict); behaviorRules:list[str]=Field(default_factory=list); referenceAssetIds:list[str]=Field(default_factory=list); providerCharacterId:str|None=None; metadata:dict[str,object]=Field(default_factory=dict)
class LocationWrite(BaseModel):
    projectId:str; name:str=Field(min_length=1,max_length=200); aliases:list[str]=Field(default_factory=list); description:str=""
    geography:dict[str,object]=Field(default_factory=dict); architecture:dict[str,object]=Field(default_factory=dict); environment:dict[str,object]=Field(default_factory=dict); visualStyle:dict[str,object]=Field(default_factory=dict); lighting:dict[str,object]=Field(default_factory=dict); weather:dict[str,object]=Field(default_factory=dict); timeOfDay:str|None=None; props:list[str]=Field(default_factory=list); rules:list[str]=Field(default_factory=list); negativeConstraints:list[str]=Field(default_factory=list); referenceAssetIds:list[str]=Field(default_factory=list); providerLocationId:str|None=None; metadata:dict[str,object]=Field(default_factory=dict)

def build_router(runtime:OrchestratorRuntime,jobs:SQLiteJobRepository)->APIRouter:
    router=APIRouter(prefix="/api/v1",tags=["content"]); store=jobs.store
    with store._lock,store.connection:
        store.connection.execute("CREATE TABLE IF NOT EXISTS content_resources (id TEXT PRIMARY KEY,resource_type TEXT NOT NULL,project_id TEXT,parent_id TEXT,title TEXT NOT NULL,description TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        store.connection.execute("CREATE INDEX IF NOT EXISTS idx_content_type_parent ON content_resources(resource_type,parent_id,created_at)")
        store.connection.execute("CREATE INDEX IF NOT EXISTS idx_content_project ON content_resources(project_id,resource_type)")
    service=JobService(jobs)
    def row_to_dict(row): return {"id":row["id"],"type":row["resource_type"],"projectId":row["project_id"],"parentId":row["parent_id"],"title":row["title"],"description":row["description"],"data":json.loads(row["payload_json"]),"createdAt":row["created_at"],"updatedAt":row["updated_at"]}
    def ensure_type(t):
        t=t.lower()
        if t not in RESOURCE_TYPES: raise HTTPException(404,"RESOURCE_TYPE_NOT_FOUND")
        return t
    def get_row(rid):
        row=store._get("content_resources",rid)
        if row is None: raise HTTPException(404,"RESOURCE_NOT_FOUND")
        return row
    def create_resource_internal(t,body,request):
        t=ensure_type(t)
        if t in {"series","episode","scene","shot"} and not body.parentId and t!="series": raise HTTPException(400,"PARENT_ID_REQUIRED")
        if t=="series" and not body.projectId: raise HTTPException(400,"PROJECT_ID_REQUIRED")
        if body.projectId and runtime.repositories.projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        rid=str(uuid.uuid4()); now=datetime.now(timezone.utc).isoformat()
        with store._lock,store.connection: store.connection.execute("INSERT INTO content_resources VALUES(?,?,?,?,?,?,?,?,?)",(rid,t,body.projectId,body.parentId,body.title,body.description,json.dumps(body.data,ensure_ascii=False,sort_keys=True),now,now))
        return {"data":{"id":rid,"type":t,"projectId":body.projectId,"parentId":body.parentId,"title":body.title,"description":body.description,"data":body.data,"createdAt":now,"updatedAt":now},"requestId":request.state.request_id}
    @router.post("/{resource_type}",status_code=201)
    def create(resource_type,body:ResourceRequest,request:Request): return create_resource_internal(resource_type,body,request)
    @router.get("/{resource_type}")
    def list_resources(resource_type,request:Request,projectId:str|None=Query(None),parentId:str|None=Query(None),page:int=Query(1,ge=1),pageSize:int=Query(50,ge=1,le=200)):
        t=ensure_type(resource_type); sql="SELECT * FROM content_resources WHERE resource_type=?"; args=[t]
        if projectId: sql+=" AND project_id=?"; args.append(projectId)
        if parentId: sql+=" AND parent_id=?"; args.append(parentId)
        sql+=" ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?"; args.extend([pageSize,(page-1)*pageSize])
        with store._lock: rows=store.connection.execute(sql,tuple(args)).fetchall()
        return {"data":[row_to_dict(r) for r in rows],"pagination":{"page":page,"pageSize":pageSize,"total":len(rows),"hasNext":len(rows)==pageSize},"requestId":request.state.request_id}
    @router.get("/{resource_type}/{resource_id}")
    def get_resource(resource_type,resource_id,request:Request):
        row=get_row(resource_id)
        if row["resource_type"]!=ensure_type(resource_type): raise HTTPException(404,"RESOURCE_NOT_FOUND")
        return {"data":row_to_dict(row),"requestId":request.state.request_id}
    @router.patch("/{resource_type}/{resource_id}")
    def patch_resource(resource_type,resource_id,body:PatchResourceRequest,request:Request):
        ensure_type(resource_type); row=get_row(resource_id)
        if row["resource_type"]!=resource_type: raise HTTPException(404,"RESOURCE_NOT_FOUND")
        now=datetime.now(timezone.utc).isoformat(); payload=body.data if body.data is not None else json.loads(row["payload_json"])
        store._insert("UPDATE content_resources SET parent_id=?,title=?,description=?,payload_json=?,updated_at=? WHERE id=?",(body.parentId if body.parentId is not None else row["parent_id"],body.title or row["title"],body.description if body.description is not None else row["description"],json.dumps(payload,ensure_ascii=False,sort_keys=True),now,resource_id))
        return {"data":row_to_dict(get_row(resource_id)),"requestId":request.state.request_id}
    def generate_internal(t,rid,request):
        t=ensure_type(t); row=get_row(rid)
        if row["resource_type"]!=t or t not in JOB_TYPES: raise HTTPException(422,"GENERATION_NOT_SUPPORTED")
        if not row["project_id"]: raise HTTPException(400,"PROJECT_ID_REQUIRED")
        job=service.create(project_id=row["project_id"],job_type=JOB_TYPES[t],target_type=t,target_id=rid,priority=50,provider="auto",model=None,input=JobInput(parameters={"resourceId":rid,"resourceType":t,"payload":json.loads(row["payload_json"])}))
        runtime.queue.enqueue(job); return {"data":{"jobId":job.id,"status":job.status.value},"requestId":request.state.request_id}
    @router.post("/{resource_type}/{resource_id}/generate",status_code=202)
    def generate(resource_type,resource_id,request:Request): return generate_internal(resource_type,resource_id,request)
    @router.post("/shots/{shot_id}/regenerate",status_code=202)
    def regenerate_shot(shot_id,request:Request): return generate_internal("shot",shot_id,request)
    @router.post("/episodes/{episode_id}/story",status_code=202)
    def create_story_for_episode(episode_id,body:ResourceRequest,request:Request):
        row=get_row(episode_id)
        if row["resource_type"]!="episode": raise HTTPException(404,"EPISODE_NOT_FOUND")
        body.projectId=row["project_id"]; body.parentId=episode_id
        return generate_internal("story",create_resource_internal("story",body,request)["data"]["id"],request)
    @router.post("/dialogues/{dialogue_id}/synthesize",status_code=202)
    def synthesize(dialogue_id,request:Request): return generate_internal("dialogue",dialogue_id,request)

    def char_data(c): return c.snapshot()|{"createdAt":c.created_at.isoformat(),"updatedAt":c.updated_at.isoformat()}
    @router.post("/characters",status_code=201,tags=["characters"])
    def create_character(body:CharacterWrite,request:Request):
        if runtime.repositories.projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        now=datetime.now(timezone.utc); c=CharacterProfile(id=f"char_{uuid.uuid4().hex}",project_id=body.projectId,name=body.name.strip(),aliases=tuple(body.aliases),description=body.description,personality=body.personality,appearance=body.appearance,voice=body.voice,speaking_style=body.speakingStyle,visual_style=body.visualStyle,behavior_rules=tuple(body.behaviorRules),reference_asset_ids=tuple(body.referenceAssetIds),provider_character_id=body.providerCharacterId,metadata=body.metadata,created_at=now,updated_at=now)
        return {"data":char_data(runtime.characters.create(c)),"requestId":request.state.request_id}
    @router.get("/characters",tags=["characters"])
    def list_characters(request:Request,projectId:str|None=None,q:str|None=None,limit:int=Query(100,ge=1,le=500)):
        items=runtime.characters.list(project_id=projectId,query=q,limit=limit); return {"data":[char_data(c) for c in items],"meta":{"count":len(items),"limit":limit},"requestId":request.state.request_id}
    @router.get("/characters/{character_id}",tags=["characters"])
    def get_character(character_id,request:Request):
        c=runtime.characters.get(character_id)
        if not c: raise HTTPException(404,"CHARACTER_NOT_FOUND")
        return {"data":char_data(c),"requestId":request.state.request_id}
    @router.put("/characters/{character_id}",tags=["characters"])
    def update_character(character_id,body:CharacterWrite,request:Request):
        old=runtime.characters.get(character_id)
        if not old: raise HTTPException(404,"CHARACTER_NOT_FOUND")
        if runtime.repositories.projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        c=CharacterProfile(id=old.id,project_id=body.projectId,name=body.name.strip(),aliases=tuple(body.aliases),description=body.description,personality=body.personality,appearance=body.appearance,voice=body.voice,speaking_style=body.speakingStyle,visual_style=body.visualStyle,behavior_rules=tuple(body.behaviorRules),reference_asset_ids=tuple(body.referenceAssetIds),provider_character_id=body.providerCharacterId,metadata=body.metadata,version=old.version,created_at=old.created_at,updated_at=old.updated_at)
        return {"data":char_data(runtime.characters.update(c)),"requestId":request.state.request_id}
    @router.delete("/characters/{character_id}",tags=["characters"])
    def delete_character(character_id,request:Request):
        if not runtime.characters.delete(character_id): raise HTTPException(404,"CHARACTER_NOT_FOUND")
        return {"data":{"id":character_id,"deleted":True},"requestId":request.state.request_id}

    def location_data(x): return x.snapshot()|{"createdAt":x.created_at.isoformat(),"updatedAt":x.updated_at.isoformat()}
    @router.post("/locations",status_code=201,tags=["locations"])
    def create_location(body:LocationWrite,request:Request):
        if runtime.repositories.projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        now=datetime.now(timezone.utc); x=LocationProfile(id=f"loc_{uuid.uuid4().hex}",project_id=body.projectId,name=body.name.strip(),aliases=tuple(body.aliases),description=body.description,geography=body.geography,architecture=body.architecture,environment=body.environment,visual_style=body.visualStyle,lighting=body.lighting,weather=body.weather,time_of_day=body.timeOfDay,props=tuple(body.props),rules=tuple(body.rules),negative_constraints=tuple(body.negativeConstraints),reference_asset_ids=tuple(body.referenceAssetIds),provider_location_id=body.providerLocationId,metadata=body.metadata,created_at=now,updated_at=now)
        return {"data":location_data(runtime.locations.create(x)),"requestId":request.state.request_id}
    @router.get("/locations",tags=["locations"])
    def list_locations(request:Request,projectId:str|None=None,q:str|None=None,limit:int=Query(100,ge=1,le=500)):
        items=runtime.locations.list(project_id=projectId,query=q,limit=limit); return {"data":[location_data(x) for x in items],"meta":{"count":len(items),"limit":limit},"requestId":request.state.request_id}
    @router.get("/locations/{location_id}",tags=["locations"])
    def get_location(location_id,request:Request):
        x=runtime.locations.get(location_id)
        if not x: raise HTTPException(404,"LOCATION_NOT_FOUND")
        return {"data":location_data(x),"requestId":request.state.request_id}
    @router.put("/locations/{location_id}",tags=["locations"])
    def update_location(location_id,body:LocationWrite,request:Request):
        old=runtime.locations.get(location_id)
        if not old: raise HTTPException(404,"LOCATION_NOT_FOUND")
        if runtime.repositories.projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        x=LocationProfile(id=old.id,project_id=body.projectId,name=body.name.strip(),aliases=tuple(body.aliases),description=body.description,geography=body.geography,architecture=body.architecture,environment=body.environment,visual_style=body.visualStyle,lighting=body.lighting,weather=body.weather,time_of_day=body.timeOfDay,props=tuple(body.props),rules=tuple(body.rules),negative_constraints=tuple(body.negativeConstraints),reference_asset_ids=tuple(body.referenceAssetIds),provider_location_id=body.providerLocationId,metadata=body.metadata,version=old.version,created_at=old.created_at,updated_at=old.updated_at)
        return {"data":location_data(runtime.locations.update(x)),"requestId":request.state.request_id}
    @router.delete("/locations/{location_id}",tags=["locations"])
    def delete_location(location_id,request:Request):
        if not runtime.locations.delete(location_id): raise HTTPException(404,"LOCATION_NOT_FOUND")
        return {"data":{"id":location_id,"deleted":True},"requestId":request.state.request_id}
    return router
