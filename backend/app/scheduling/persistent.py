from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4
from zoneinfo import ZoneInfo
import json

from ..infrastructure.sqlite import SQLiteStore, _dt, _parse_dt, _json

@dataclass(slots=True)
class Schedule:
    id: str
    project_id: str
    operation: str
    payload: dict
    run_at: datetime
    cron: str | None = None
    interval_seconds: int | None = None
    timezone_name: str = "UTC"
    enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class SQLiteScheduleRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store=store
        with store._lock, store.connection:
            store.connection.execute("""CREATE TABLE IF NOT EXISTS schedules (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, operation TEXT NOT NULL, payload_json TEXT NOT NULL, run_at TEXT NOT NULL, cron TEXT, interval_seconds INTEGER, timezone_name TEXT NOT NULL DEFAULT 'UTC', enabled INTEGER NOT NULL DEFAULT 1, last_run_at TEXT, next_run_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(enabled,next_run_at)")
    def create(self,schedule:Schedule)->Schedule:
        now=datetime.now(timezone.utc); schedule.created_at=now; schedule.updated_at=now; schedule.run_at=schedule.run_at.astimezone(timezone.utc); schedule.next_run_at=(schedule.next_run_at or schedule.run_at).astimezone(timezone.utc)
        self.store._insert("INSERT INTO schedules(id,project_id,operation,payload_json,run_at,cron,interval_seconds,timezone_name,enabled,last_run_at,next_run_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(schedule.id,schedule.project_id,schedule.operation,_json(schedule.payload),_dt(schedule.run_at),schedule.cron,schedule.interval_seconds,schedule.timezone_name,int(schedule.enabled),_dt(schedule.last_run_at),_dt(schedule.next_run_at),_dt(schedule.created_at),_dt(schedule.updated_at)))
        return schedule
    def _row(self,row):
        if not row:return None
        return Schedule(id=row["id"],project_id=row["project_id"],operation=row["operation"],payload=json.loads(row["payload_json"]),run_at=_parse_dt(row["run_at"]),cron=row["cron"],interval_seconds=row["interval_seconds"],timezone_name=row["timezone_name"],enabled=bool(row["enabled"]),last_run_at=_parse_dt(row["last_run_at"]),next_run_at=_parse_dt(row["next_run_at"]),created_at=_parse_dt(row["created_at"]),updated_at=_parse_dt(row["updated_at"]))
    def get(self,schedule_id):
        with self.store._lock:return self._row(self.store.connection.execute("SELECT * FROM schedules WHERE id=?",(schedule_id,)).fetchone())
    def list(self,project_id=None,enabled=None,limit=200):
        clauses=[];params=[]
        if project_id:clauses.append("project_id=?");params.append(project_id)
        if enabled is not None:clauses.append("enabled=?");params.append(int(enabled))
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        with self.store._lock:rows=self.store.connection.execute(f"SELECT * FROM schedules{where} ORDER BY next_run_at,id LIMIT ?",(*params,max(1,min(limit,500)))).fetchall()
        return [self._row(r) for r in rows]
    def due(self,now,limit=50):
        with self.store._lock:rows=self.store.connection.execute("SELECT * FROM schedules WHERE enabled=1 AND next_run_at IS NOT NULL AND next_run_at<=? ORDER BY next_run_at,id LIMIT ?",(_dt(now.astimezone(timezone.utc)),max(1,min(limit,200)))).fetchall()
        return [self._row(r) for r in rows]
    def update(self,schedule):
        schedule.updated_at=datetime.now(timezone.utc)
        with self.store._lock,self.store.connection:self.store.connection.execute("UPDATE schedules SET operation=?,payload_json=?,run_at=?,cron=?,interval_seconds=?,timezone_name=?,enabled=?,last_run_at=?,next_run_at=?,updated_at=? WHERE id=?",(schedule.operation,_json(schedule.payload),_dt(schedule.run_at),schedule.cron,schedule.interval_seconds,schedule.timezone_name,int(schedule.enabled),_dt(schedule.last_run_at),_dt(schedule.next_run_at),_dt(schedule.updated_at),schedule.id))
        return schedule
    def delete(self,schedule_id):
        with self.store._lock,self.store.connection:
            cur=self.store.connection.execute("DELETE FROM schedules WHERE id=?",(schedule_id,));return cur.rowcount==1

def _field_matches(value:int,token:str,minimum:int,maximum:int)->bool:
    if token=="*":return True
    for part in token.split(","):
        base,_,step=part.partition("/");step_n=int(step) if step else 1
        if step_n<1:continue
        if base=="*":
            if (value-minimum)%step_n==0:return True
        elif "-" in base:
            a,b=base.split("-",1)
            if int(a)<=value<=int(b) and (value-int(a))%step_n==0:return True
        elif value==int(base):return True
    return False

def cron_matches(dt:datetime,expression:str)->bool:
    fields=expression.split()
    if len(fields)!=5:raise ValueError("CRON_MUST_HAVE_5_FIELDS")
    minute,hour,dom,month,dow=fields
    return _field_matches(dt.minute,minute,0,59) and _field_matches(dt.hour,hour,0,23) and _field_matches(dt.day,dom,1,31) and _field_matches(dt.month,month,1,12) and _field_matches((dt.weekday()+1)%7,dow,0,6)

def next_cron_time(start:datetime,expression:str,tz_name:str="UTC",horizon_minutes:int=366*24*60)->datetime:
    tz=ZoneInfo(tz_name); local=start.astimezone(tz).replace(second=0,microsecond=0,tzinfo=tz)+timedelta(minutes=1)
    for _ in range(horizon_minutes):
        if cron_matches(local,expression):return local.astimezone(timezone.utc)
        local+=timedelta(minutes=1)
    raise ValueError("CRON_NEXT_RUN_NOT_FOUND")

class PersistentScheduler:
    def __init__(self,repository:SQLiteScheduleRepository,enqueue):self.repository=repository;self.enqueue=enqueue;self._lock=RLock()
    def tick(self,now=None,limit=50):
        now=now or datetime.now(timezone.utc);created=[]
        for schedule in self.repository.due(now,limit):
            with self._lock:
                current=self.repository.get(schedule.id)
                if not current or not current.enabled or not current.next_run_at or current.next_run_at>now:continue
                child=self.enqueue(current);created.append(child.id if hasattr(child,"id") else str(child));current.last_run_at=now
                if current.cron:current.next_run_at=next_cron_time(now,current.cron,current.timezone_name)
                elif current.interval_seconds:current.next_run_at=now+timedelta(seconds=current.interval_seconds)
                else:current.enabled=False;current.next_run_at=None
                self.repository.update(current)
        return created
    def pause(self,schedule_id):
        s=self.repository.get(schedule_id)
        if not s:raise KeyError("SCHEDULE_NOT_FOUND")
        s.enabled=False;return self.repository.update(s)
    def resume(self,schedule_id):
        s=self.repository.get(schedule_id)
        if not s:raise KeyError("SCHEDULE_NOT_FOUND")
        s.enabled=True
        if s.next_run_at is None:s.next_run_at=datetime.now(timezone.utc)
        return self.repository.update(s)
