from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from ..domain.characters import CharacterProfile
from ..domain.character_repositories import CharacterRepository
from .sqlite import SQLiteStore


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _loads(value: str | None, default):
    return json.loads(value) if value else default


class SQLiteCharacterRepository(CharacterRepository):
    """Persistent reusable character library. Character identity is kept separate from generated assets."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        with store._lock, store.connection:
            store.connection.execute("""CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]', description TEXT NOT NULL DEFAULT '',
                personality_json TEXT NOT NULL DEFAULT '{}', appearance_json TEXT NOT NULL DEFAULT '{}',
                voice_json TEXT NOT NULL DEFAULT '{}', speaking_style_json TEXT NOT NULL DEFAULT '{}',
                visual_style_json TEXT NOT NULL DEFAULT '{}', behavior_rules_json TEXT NOT NULL DEFAULT '[]',
                reference_asset_ids_json TEXT NOT NULL DEFAULT '[]', provider_character_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_characters_project_name ON characters(project_id,name)")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_characters_provider ON characters(provider_character_id)")

    def _from_row(self, row: sqlite3.Row) -> CharacterProfile:
        return CharacterProfile(
            id=row["id"], project_id=row["project_id"], name=row["name"],
            aliases=tuple(_loads(row["aliases_json"], [])), description=row["description"] or "",
            personality=_loads(row["personality_json"], {}), appearance=_loads(row["appearance_json"], {}),
            voice=_loads(row["voice_json"], {}), speaking_style=_loads(row["speaking_style_json"], {}),
            visual_style=_loads(row["visual_style_json"], {}), behavior_rules=tuple(_loads(row["behavior_rules_json"], [])),
            reference_asset_ids=tuple(_loads(row["reference_asset_ids_json"], [])),
            provider_character_id=row["provider_character_id"], metadata=_loads(row["metadata_json"], {}),
            version=int(row["version"]), created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(self, character: CharacterProfile) -> CharacterProfile:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("""INSERT INTO characters
                (id,project_id,name,aliases_json,description,personality_json,appearance_json,voice_json,
                 speaking_style_json,visual_style_json,behavior_rules_json,reference_asset_ids_json,
                 provider_character_id,metadata_json,version,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (character.id, character.project_id, character.name, json.dumps(character.aliases), character.description,
                 json.dumps(character.personality, ensure_ascii=False), json.dumps(character.appearance, ensure_ascii=False),
                 json.dumps(character.voice, ensure_ascii=False), json.dumps(character.speaking_style, ensure_ascii=False),
                 json.dumps(character.visual_style, ensure_ascii=False), json.dumps(character.behavior_rules, ensure_ascii=False),
                 json.dumps(character.reference_asset_ids, ensure_ascii=False), character.provider_character_id,
                 json.dumps(character.metadata, ensure_ascii=False), character.version, _dt(character.created_at), _dt(character.updated_at)))
        return character

    def get(self, character_id: str) -> CharacterProfile | None:
        with self.store._lock:
            row = self.store.connection.execute("SELECT * FROM characters WHERE id=?", (character_id,)).fetchone()
        return self._from_row(row) if row else None

    def update(self, character: CharacterProfile) -> CharacterProfile:
        updated = CharacterProfile(**{**character.__dict__, "version": character.version + 1, "updated_at": datetime.now(timezone.utc)}) if hasattr(character, "__dict__") else character
        if updated is character:
            updated = CharacterProfile(id=character.id, project_id=character.project_id, name=character.name,
                aliases=character.aliases, description=character.description, personality=character.personality,
                appearance=character.appearance, voice=character.voice, speaking_style=character.speaking_style,
                visual_style=character.visual_style, behavior_rules=character.behavior_rules,
                reference_asset_ids=character.reference_asset_ids, provider_character_id=character.provider_character_id,
                metadata=character.metadata, version=character.version + 1, created_at=character.created_at,
                updated_at=datetime.now(timezone.utc))
        with self.store._lock, self.store.connection:
            cur = self.store.connection.execute("""UPDATE characters SET name=?,aliases_json=?,description=?,personality_json=?,appearance_json=?,voice_json=?,
                speaking_style_json=?,visual_style_json=?,behavior_rules_json=?,reference_asset_ids_json=?,provider_character_id=?,metadata_json=?,version=?,updated_at=? WHERE id=?""",
                (updated.name, json.dumps(updated.aliases), updated.description, json.dumps(updated.personality, ensure_ascii=False),
                 json.dumps(updated.appearance, ensure_ascii=False), json.dumps(updated.voice, ensure_ascii=False), json.dumps(updated.speaking_style, ensure_ascii=False),
                 json.dumps(updated.visual_style, ensure_ascii=False), json.dumps(updated.behavior_rules, ensure_ascii=False), json.dumps(updated.reference_asset_ids, ensure_ascii=False),
                 updated.provider_character_id, json.dumps(updated.metadata, ensure_ascii=False), updated.version, _dt(updated.updated_at), updated.id))
            if cur.rowcount != 1:
                raise KeyError("CHARACTER_NOT_FOUND")
        return updated

    def delete(self, character_id: str) -> bool:
        with self.store._lock, self.store.connection:
            cur = self.store.connection.execute("DELETE FROM characters WHERE id=?", (character_id,))
            return cur.rowcount == 1

    def list(self, *, project_id: str | None = None, query: str | None = None, limit: int = 100) -> list[CharacterProfile]:
        limit = max(1, min(int(limit), 500))
        clauses, params = [], []
        if project_id:
            clauses.append("project_id=?"); params.append(project_id)
        if query:
            clauses.append("(name LIKE ? OR description LIKE ? OR aliases_json LIKE ?)")
            pattern = f"%{query}%"; params.extend([pattern, pattern, pattern])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.store._lock:
            rows = self.store.connection.execute(f"SELECT * FROM characters{where} ORDER BY updated_at DESC,name LIMIT ?", (*params, limit)).fetchall()
        return [self._from_row(row) for row in rows]
