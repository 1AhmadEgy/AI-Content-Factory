from __future__ import annotations
import json
from datetime import datetime, timezone
from .sqlite import SQLiteStore
from ..domain.locations import LocationProfile
from ..domain.location_repositories import LocationRepository

class SQLiteLocationRepository(LocationRepository):
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        with store._lock, store.connection:
            store.connection.execute("CREATE TABLE IF NOT EXISTS locations (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, aliases_json TEXT NOT NULL, description TEXT NOT NULL, geography_json TEXT NOT NULL, architecture_json TEXT NOT NULL, environment_json TEXT NOT NULL, visual_style_json TEXT NOT NULL, lighting_json TEXT NOT NULL, weather_json TEXT NOT NULL, time_of_day TEXT, props_json TEXT NOT NULL, rules_json TEXT NOT NULL, negative_constraints_json TEXT NOT NULL, reference_asset_ids_json TEXT NOT NULL, provider_location_id TEXT, metadata_json TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_locations_project_name ON locations(project_id,name)")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_locations_provider ON locations(provider_location_id)")

    @staticmethod
    def _json(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    @staticmethod
    def _from_row(r):
        return LocationProfile(id=r["id"], project_id=r["project_id"], name=r["name"], aliases=tuple(json.loads(r["aliases_json"])), description=r["description"], geography=json.loads(r["geography_json"]), architecture=json.loads(r["architecture_json"]), environment=json.loads(r["environment_json"]), visual_style=json.loads(r["visual_style_json"]), lighting=json.loads(r["lighting_json"]), weather=json.loads(r["weather_json"]), time_of_day=r["time_of_day"], props=tuple(json.loads(r["props_json"])), rules=tuple(json.loads(r["rules_json"])), negative_constraints=tuple(json.loads(r["negative_constraints_json"])), reference_asset_ids=tuple(json.loads(r["reference_asset_ids_json"])), provider_location_id=r["provider_location_id"], metadata=json.loads(r["metadata_json"]), version=r["version"], created_at=datetime.fromisoformat(r["created_at"]), updated_at=datetime.fromisoformat(r["updated_at"]))

    def create(self, location):
        now = datetime.now(timezone.utc)
        created_at = location.created_at or now
        updated_at = location.updated_at or created_at
        with self.store._lock, self.store.connection:
            self.store.connection.execute("INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (location.id,location.project_id,location.name,self._json(location.aliases),location.description,self._json(location.geography),self._json(location.architecture),self._json(location.environment),self._json(location.visual_style),self._json(location.lighting),self._json(location.weather),location.time_of_day,self._json(location.props),self._json(location.rules),self._json(location.negative_constraints),self._json(location.reference_asset_ids),location.provider_location_id,self._json(location.metadata),location.version,created_at.isoformat(),updated_at.isoformat()))
        return location
    def get(self, location_id):
        r=self.store._get("locations",location_id); return self._from_row(r) if r else None
    def update(self, location):
        now=datetime.now(timezone.utc); version=location.version+1
        with self.store._lock, self.store.connection:
            self.store.connection.execute("UPDATE locations SET project_id=?,name=?,aliases_json=?,description=?,geography_json=?,architecture_json=?,environment_json=?,visual_style_json=?,lighting_json=?,weather_json=?,time_of_day=?,props_json=?,rules_json=?,negative_constraints_json=?,reference_asset_ids_json=?,provider_location_id=?,metadata_json=?,version=?,updated_at=? WHERE id=?", (location.project_id,location.name,self._json(location.aliases),location.description,self._json(location.geography),self._json(location.architecture),self._json(location.environment),self._json(location.visual_style),self._json(location.lighting),self._json(location.weather),location.time_of_day,self._json(location.props),self._json(location.rules),self._json(location.negative_constraints),self._json(location.reference_asset_ids),location.provider_location_id,self._json(location.metadata),version,now.isoformat(),location.id))
        return self.get(location.id)
    def delete(self, location_id):
        with self.store._lock, self.store.connection:
            c=self.store.connection.execute("DELETE FROM locations WHERE id=?",(location_id,))
        return c.rowcount==1
    def list(self, *, project_id=None, query=None, limit=100):
        clauses=[]; args=[]
        if project_id: clauses.append("project_id=?"); args.append(project_id)
        if query:
            clauses.append("(name LIKE ? OR description LIKE ? OR aliases_json LIKE ?)"); q=f"%{query}%"; args.extend([q,q,q])
        where=" WHERE "+" AND ".join(clauses) if clauses else ""
        with self.store._lock: rows=self.store.connection.execute(f"SELECT * FROM locations{where} ORDER BY name COLLATE NOCASE LIMIT ?",(*args,max(1,min(limit,500)))).fetchall()
        return [self._from_row(r) for r in rows]
