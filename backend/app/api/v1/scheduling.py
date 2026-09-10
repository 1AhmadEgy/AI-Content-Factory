from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from ...infrastructure.sqlite import SQLiteProjectRepository
from ...scheduling.persistent import PersistentScheduler, Schedule, SQLiteScheduleRepository, cron_matches, next_cron_time

router=APIRouter(prefix="/api/v1/schedules",tags=["scheduling"])

class ScheduleRequest(BaseModel):
    projectId:str; operation:str=Field(min_length=1,max_length=100); payload:dict[str,Any]=Field(default_factory=dict)
    runAt:datetime|None=None; cron:str|None=None; intervalSeconds:int|None=Field(default=None,ge=1,le=31536000); timezone:str="UTC"
    @model_validator(mode="after")
    def validate_schedule(self):
        if not self.cron and not self.intervalSeconds and not self.runAt:raise ValueError("ONE_OF_RUN_AT_CRON_INTERVAL_REQUIRED")
        if self.cron and self.intervalSeconds:raise ValueError("CRON_AND_INTERVAL_ARE_MUTUALLY_EXCLUSIVE")
        try:ZoneInfo(self.timezone)
        except Exception as e:raise ValueError("INVALID_TIMEZONE") from e
        if self.cron:
            try:cron_matches(datetime.now(ZoneInfo(self.timezone)),self.cron)
            except Exception as e:raise ValueError(str(e)) from e
        return self

def _serialize(s:Schedule)->dict[str,Any]:return {"id":s.id,"projectId":s.project_id,"operation":s.operation,"payload":s.payload,"runAt":s.run_at.isoformat(),"cron":s.cron,"intervalSeconds":s.interval_seconds,"timezone":s.timezone_name,"enabled":s.enabled,"lastRunAt":s.last_run_at.isoformat() if s.last_run_at else None,"nextRunAt":s.next_run_at.isoformat() if s.next_run_at else None,"createdAt":s.created_at.isoformat(),"updatedAt":s.updated_at.isoformat()}

def build_router(projects:SQLiteProjectRepository,schedules:SQLiteScheduleRepository,scheduler:PersistentScheduler)->APIRouter:
    @router.get("")
    def list_schedules(request:Request,project_id:str|None=None,enabled:bool|None=None):
        data=[_serialize(s) for s in schedules.list(project_id,enabled)];return {"data":data,"meta":{"count":len(data)},"requestId":request.state.request_id}
    @router.post("",status_code=202)
    def create_schedule(body:ScheduleRequest,request:Request):
        if projects.get(body.projectId) is None:raise HTTPException(404,"PROJECT_NOT_FOUND")
        now=datetime.now(timezone.utc);run_at=body.runAt or now;run_at=run_at.replace(tzinfo=timezone.utc) if run_at.tzinfo is None else run_at.astimezone(timezone.utc)
        next_run=next_cron_time(run_at,body.cron,body.timezone) if body.cron else run_at
        s=Schedule(id="sch_"+uuid4().hex,project_id=body.projectId,operation=body.operation,payload=body.payload,run_at=run_at,cron=body.cron,interval_seconds=body.intervalSeconds,timezone_name=body.timezone,next_run_at=next_run)
        schedules.create(s);return {"data":_serialize(s),"requestId":request.state.request_id}
    @router.get("/{schedule_id}")
    def get_schedule(schedule_id:str,request:Request):
        s=schedules.get(schedule_id)
        if not s:raise HTTPException(404,"SCHEDULE_NOT_FOUND")
        return {"data":_serialize(s),"requestId":request.state.request_id}
    @router.post("/{schedule_id}/pause")
    def pause_schedule(schedule_id:str,request:Request):
        try:s=scheduler.pause(schedule_id)
        except KeyError as e:raise HTTPException(404,str(e.args[0])) from e
        return {"data":_serialize(s),"requestId":request.state.request_id}
    @router.post("/{schedule_id}/resume")
    def resume_schedule(schedule_id:str,request:Request):
        try:s=scheduler.resume(schedule_id)
        except KeyError as e:raise HTTPException(404,str(e.args[0])) from e
        return {"data":_serialize(s),"requestId":request.state.request_id}
    @router.delete("/{schedule_id}",status_code=204)
    def delete_schedule(schedule_id:str):
        if not schedules.delete(schedule_id):raise HTTPException(404,"SCHEDULE_NOT_FOUND")
    @router.post("/maintenance/tick")
    def tick(request:Request):return {"data":{"createdJobIds":scheduler.tick()},"requestId":request.state.request_id}
    return router
