from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository
from ...orchestrator.batch_service import BatchItem, BatchService
from ...orchestrator.runtime import OrchestratorRuntime

router=APIRouter(prefix="/api/v1/batches",tags=["batch"])

class BatchItemRequest(BaseModel):
    type: JobType
    targetType: str=Field(min_length=1)
    targetId: str|None=None
    parameters: dict[str,Any]=Field(default_factory=dict)
    referenceAssetIds: list[str]=Field(default_factory=list)
    constraints: dict[str,Any]=Field(default_factory=dict)
    seed: int|None=None
    deterministic: bool=False
    priority: int=100
    maxAttempts: int=Field(default=3,ge=1,le=20)
    provider: str|None=None
    model: str|None=None

class CreateBatchRequest(BaseModel):
    projectId: str
    items: list[BatchItemRequest]=Field(min_length=1,max_length=500)
    priority: int=100

def _job(j):
    return {"id":j.id,"type":j.type.value,"status":j.status.value,"progress":j.progress,"targetType":j.target_type,"targetId":j.target_id,"attempt":j.attempt,"maxAttempts":j.max_attempts}

def _summary(s):
    return {k:([_job(j) for j in v] if k=="children" else v.value if hasattr(v,"value") else v) for k,v in s.items()}

def build_router(projects:SQLiteProjectRepository,jobs:SQLiteJobRepository,runtime:OrchestratorRuntime)->APIRouter:
    service=BatchService(jobs,runtime.queue.enqueue)
    @router.post("",status_code=202)
    def create_batch(body:CreateBatchRequest,request:Request):
        if projects.get(body.projectId) is None: raise HTTPException(404,"PROJECT_NOT_FOUND")
        items=[BatchItem(type=i.type,target_type=i.targetType,target_id=i.targetId,input=JobInput(parameters=i.parameters,reference_asset_ids=i.referenceAssetIds,constraints=i.constraints,seed=i.seed,deterministic=i.deterministic),priority=i.priority,max_attempts=i.maxAttempts,provider=i.provider,model=i.model) for i in body.items]
        parent=service.create(body.projectId,items,body.priority)
        return {"data":{"batchId":parent.id,"status":parent.status.value,"itemCount":len(items)},"requestId":request.state.request_id}
    @router.get("/{batch_id}")
    def get_batch(batch_id:str,request:Request):
        try: data=service.summary(batch_id)
        except KeyError as e: raise HTTPException(404,str(e.args[0])) from e
        return {"data":_summary(data),"requestId":request.state.request_id}
    @router.post("/{batch_id}/cancel")
    def cancel_batch(batch_id:str,request:Request):
        try:data=service.cancel(batch_id)
        except KeyError as e:raise HTTPException(404,str(e.args[0])) from e
        return {"data":_summary(data),"requestId":request.state.request_id}
    @router.post("/{batch_id}/retry")
    def retry_batch(batch_id:str,request:Request):
        try:data=service.retry_failed(batch_id)
        except KeyError as e:raise HTTPException(404,str(e.args[0])) from e
        return {"data":_summary(data),"requestId":request.state.request_id}
    return router
