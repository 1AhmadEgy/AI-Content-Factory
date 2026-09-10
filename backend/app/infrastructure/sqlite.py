from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..domain.jobs import GenerationJob, JobInput, JobOutput, JobStatus, JobType
from ..domain.projects import Episode, Project, Scene, Shot
from ..domain.repositories import EpisodeRepository, JobRepository, ProjectRepository, SceneRepository, ShotRepository


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class SQLiteStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        import threading
        self._lock = threading.RLock()
        db_path = str(path)
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._configure_connection(db_path)
        self.initialize()

    def _configure_connection(self, db_path: str) -> None:
        """Apply low-risk SQLite settings for file-backed performance."""
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 5000")
            self._connection.execute("PRAGMA temp_store = MEMORY")
            self._connection.execute("PRAGMA cache_size = -20000")
            if db_path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")
                self._connection.execute("PRAGMA synchronous = NORMAL")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS episodes (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_episodes_project ON episodes(project_id);
                CREATE TABLE IF NOT EXISTS scenes (id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE, title TEXT NOT NULL, order_index INTEGER NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_scenes_episode_order ON scenes(episode_id, order_index);
                CREATE TABLE IF NOT EXISTS shots (id TEXT PRIMARY KEY, scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE, order_index INTEGER NOT NULL, prompt TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_shots_scene_order ON shots(scene_id, order_index);
                CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, parent_job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, type TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT, priority INTEGER NOT NULL, status TEXT NOT NULL, progress REAL NOT NULL, attempt INTEGER NOT NULL, max_attempts INTEGER NOT NULL, provider TEXT, model TEXT, input_json TEXT NOT NULL, output_json TEXT, error_code TEXT, error_message TEXT, created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_jobs_project_status ON jobs(project_id, status);
                CREATE INDEX IF NOT EXISTS idx_jobs_status_priority ON jobs(status, priority, created_at);
                CREATE TABLE IF NOT EXISTS idempotency_keys (key TEXT PRIMARY KEY, operation TEXT NOT NULL, request_fingerprint TEXT NOT NULL, resource_id TEXT NOT NULL, created_at TEXT NOT NULL);
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _get(self, table: str, entity_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()

    def _insert(self, sql: str, values: tuple[Any, ...]) -> None:
        with self._lock, self._connection:
            self._connection.execute(sql, values)

    def get_idempotency(self, key: str, operation: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute("SELECT * FROM idempotency_keys WHERE key = ? AND operation = ?", (key, operation)).fetchone()

    def claim_idempotency(self, key: str, operation: str, fingerprint: str, resource_id: str) -> bool:
        with self._lock, self._connection:
            try:
                self._connection.execute("INSERT INTO idempotency_keys(key,operation,request_fingerprint,resource_id,created_at) VALUES(?,?,?,?,?)", (key, operation, fingerprint, resource_id, datetime.now().astimezone().isoformat()))
                return True
            except sqlite3.IntegrityError:
                return False


class SQLiteProjectRepository(ProjectRepository):
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def create(self, project: Project) -> Project:
        self.store._insert("INSERT INTO projects(id,name,created_at,updated_at) VALUES(?,?,?,?)", (project.id, project.name, _dt(project.created_at), _dt(project.updated_at)))
        return project

    def get(self, project_id: str) -> Project | None:
        row = self.store._get("projects", project_id)
        return Project(row["id"], row["name"], _parse_dt(row["created_at"]), _parse_dt(row["updated_at"])) if row else None

    def list(self, limit: int, offset: int) -> tuple[list[Project], int]:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        with self.store._lock:
            total = self.store.connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            rows = self.store.connection.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [Project(r["id"], r["name"], _parse_dt(r["created_at"]), _parse_dt(r["updated_at"])) for r in rows], total

    def update(self, project: Project) -> Project:
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute("UPDATE projects SET name=?, updated_at=? WHERE id=?", (project.name, _dt(project.updated_at), project.id))
            if cursor.rowcount != 1:
                raise KeyError(f"Project not found: {project.id}")
        return project

    def delete(self, project_id: str) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("DELETE FROM projects WHERE id=?", (project_id,))


class SQLiteEpisodeRepository(EpisodeRepository):
    def __init__(self, store: SQLiteStore) -> None: self.store = store
    def create(self, episode: Episode) -> Episode:
        self.store._insert("INSERT INTO episodes(id,project_id,title,created_at,updated_at) VALUES(?,?,?,?,?)", (episode.id, episode.project_id, episode.title, _dt(episode.created_at), _dt(episode.updated_at))); return episode
    def get(self, episode_id: str) -> Episode | None:
        row = self.store._get("episodes", episode_id); return Episode(row["id"], row["project_id"], row["title"], _parse_dt(row["created_at"]), _parse_dt(row["updated_at"])) if row else None


class SQLiteSceneRepository(SceneRepository):
    def __init__(self, store: SQLiteStore) -> None: self.store = store
    def create(self, scene: Scene) -> Scene:
        self.store._insert("INSERT INTO scenes(id,episode_id,title,order_index,created_at) VALUES(?,?,?,?,?)", (scene.id, scene.episode_id, scene.title, scene.order_index, _dt(scene.created_at))); return scene
    def get(self, scene_id: str) -> Scene | None:
        row = self.store._get("scenes", scene_id); return Scene(row["id"], row["episode_id"], row["title"], row["order_index"], _parse_dt(row["created_at"])) if row else None


class SQLiteShotRepository(ShotRepository):
    def __init__(self, store: SQLiteStore) -> None: self.store = store
    def create(self, shot: Shot) -> Shot:
        self.store._insert("INSERT INTO shots(id,scene_id,order_index,prompt,created_at) VALUES(?,?,?,?,?)", (shot.id, shot.scene_id, shot.order_index, shot.prompt, _dt(shot.created_at))); return shot
    def get(self, shot_id: str) -> Shot | None:
        row = self.store._get("shots", shot_id); return Shot(row["id"], row["scene_id"], row["order_index"], row["prompt"], _parse_dt(row["created_at"])) if row else None


def _job_input_to_dict(value: JobInput) -> dict[str, Any]: return {"parameters": value.parameters, "referenceAssetIds": value.reference_asset_ids, "constraints": value.constraints, "seed": value.seed, "deterministic": value.deterministic}
def _job_input_from_dict(value: dict[str, Any]) -> JobInput: return JobInput(parameters=value.get("parameters", {}), reference_asset_ids=value.get("referenceAssetIds", []), constraints=value.get("constraints", {}), seed=value.get("seed"), deterministic=value.get("deterministic", False))
def _job_output_to_dict(value: JobOutput | None) -> dict[str, Any] | None: return None if value is None else {"assetIds": value.asset_ids, "metrics": value.metrics, "providerRunId": value.provider_run_id}
def _job_output_from_dict(value: dict[str, Any] | None) -> JobOutput | None: return None if value is None else JobOutput(asset_ids=value.get("assetIds", []), metrics=value.get("metrics", {}), provider_run_id=value.get("providerRunId"))
def _job_from_row(row: sqlite3.Row) -> GenerationJob:
    return GenerationJob(id=row["id"], parent_job_id=row["parent_job_id"], project_id=row["project_id"], type=JobType(row["type"]), target_type=row["target_type"], target_id=row["target_id"], priority=row["priority"], status=JobStatus(row["status"]), progress=row["progress"], attempt=row["attempt"], max_attempts=row["max_attempts"], provider=row["provider"], model=row["model"], input=_job_input_from_dict(json.loads(row["input_json"])), output=_job_output_from_dict(json.loads(row["output_json"]) if row["output_json"] else None), error_code=row["error_code"], error_message=row["error_message"], created_at=_parse_dt(row["created_at"]), started_at=_parse_dt(row["started_at"]), completed_at=_parse_dt(row["completed_at"]), updated_at=_parse_dt(row["updated_at"]))


class SQLiteJobRepository(JobRepository):
    def __init__(self, store: SQLiteStore) -> None: self.store = store
    def create(self, job: GenerationJob) -> GenerationJob:
        self.store._insert("INSERT INTO jobs(id,parent_job_id,project_id,type,target_type,target_id,priority,status,progress,attempt,max_attempts,provider,model,input_json,output_json,error_code,error_message,created_at,started_at,completed_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (job.id, job.parent_job_id, job.project_id, job.type.value, job.target_type, job.target_id, job.priority, job.status.value, job.progress, job.attempt, job.max_attempts, job.provider, job.model, _json(_job_input_to_dict(job.input)), _json(_job_output_to_dict(job.output)) if job.output else None, job.error_code, job.error_message, _dt(job.created_at), _dt(job.started_at), _dt(job.completed_at), _dt(job.updated_at))); return job
    def get(self, job_id: str) -> GenerationJob | None:
        row = self.store._get("jobs", job_id); return _job_from_row(row) if row else None
    def update(self, job: GenerationJob) -> GenerationJob:
        with self.store._lock, self.store.connection:
            cursor = self.store.connection.execute("UPDATE jobs SET parent_job_id=?,project_id=?,type=?,target_type=?,target_id=?,priority=?,status=?,progress=?,attempt=?,max_attempts=?,provider=?,model=?,input_json=?,output_json=?,error_code=?,error_message=?,created_at=?,started_at=?,completed_at=?,updated_at=? WHERE id=?", (job.parent_job_id, job.project_id, job.type.value, job.target_type, job.target_id, job.priority, job.status.value, job.progress, job.attempt, job.max_attempts, job.provider, job.model, _json(_job_input_to_dict(job.input)), _json(_job_output_to_dict(job.output)) if job.output else None, job.error_code, job.error_message, _dt(job.created_at), _dt(job.started_at), _dt(job.completed_at), _dt(job.updated_at), job.id))
            if cursor.rowcount != 1: raise KeyError(f"Job not found: {job.id}")
        return job


class SQLiteRepositories:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.store = SQLiteStore(path); self.projects = SQLiteProjectRepository(self.store); self.episodes = SQLiteEpisodeRepository(self.store); self.scenes = SQLiteSceneRepository(self.store); self.shots = SQLiteShotRepository(self.store); self.jobs = SQLiteJobRepository(self.store)
    def close(self) -> None: self.store.close()
