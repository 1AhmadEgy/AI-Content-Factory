from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .sqlite import SQLiteStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ShotCharacterLink:
    id: str
    shot_id: str
    character_id: str
    position_order: int = 0
    action: str | None = None
    emotion: str | None = None
    dialogue: str | None = None
    pose: str | None = None
    expression_override: str | None = None
    is_speaking: bool = False
    voice_audio_asset_id: str | None = None
    extra_data: dict[str, Any] | None = None


class SQLiteShotCompositionRepository:
    """Normalized shot/character/location links plus persisted shot-generation metadata."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS shot_characters (
                    id TEXT PRIMARY KEY,
                    shot_id TEXT NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
                    character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    position_order INTEGER NOT NULL DEFAULT 0,
                    action TEXT,
                    emotion TEXT,
                    dialogue TEXT,
                    pose TEXT,
                    expression_override TEXT,
                    is_speaking INTEGER NOT NULL DEFAULT 0,
                    voice_audio_asset_id TEXT,
                    extra_data_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(shot_id, character_id)
                );
                CREATE INDEX IF NOT EXISTS idx_shot_characters_shot_order ON shot_characters(shot_id, position_order);
                CREATE INDEX IF NOT EXISTS idx_shot_characters_character ON shot_characters(character_id);

                CREATE TABLE IF NOT EXISTS shot_locations (
                    id TEXT PRIMARY KEY,
                    shot_id TEXT NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
                    location_id TEXT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
                    time_of_day_override TEXT,
                    weather_override TEXT,
                    atmosphere_override TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(shot_id)
                );
                CREATE INDEX IF NOT EXISTS idx_shot_locations_location ON shot_locations(location_id);
                """
            )
            columns = {r["name"] for r in self.store.connection.execute("PRAGMA table_info(shots)").fetchall()}
            additions = {
                "generated_negative_prompt": "TEXT",
                "generated_image_asset_id": "TEXT",
                "generation_status": "TEXT NOT NULL DEFAULT 'pending'",
                "generation_error": "TEXT",
                "continuity_hash": "TEXT",
                "camera_angle": "TEXT NOT NULL DEFAULT 'medium'",
                "mood": "TEXT",
                "visual_style_json": "TEXT NOT NULL DEFAULT '{}'",
            }
            for name, definition in additions.items():
                if name not in columns:
                    self.store.connection.execute(f"ALTER TABLE shots ADD COLUMN {name} {definition}")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_shots_generation_status ON shots(generation_status)")

    def replace_characters(self, links: list[ShotCharacterLink]) -> None:
        if not links:
            return
        shot_id = links[0].shot_id
        if any(link.shot_id != shot_id for link in links):
            raise ValueError("ALL_LINKS_MUST_TARGET_ONE_SHOT")
        with self.store._lock, self.store.connection:
            self.store.connection.execute("DELETE FROM shot_characters WHERE shot_id=?", (shot_id,))
            for link in links:
                self.store.connection.execute(
                    """INSERT INTO shot_characters
                    (id,shot_id,character_id,position_order,action,emotion,dialogue,pose,expression_override,is_speaking,voice_audio_asset_id,extra_data_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (link.id, link.shot_id, link.character_id, link.position_order, link.action, link.emotion, link.dialogue,
                     link.pose, link.expression_override, int(link.is_speaking), link.voice_audio_asset_id,
                     json.dumps(link.extra_data or {}, ensure_ascii=False), _now()),
                )

    def list_characters(self, shot_id: str) -> list[ShotCharacterLink]:
        with self.store._lock:
            rows = self.store.connection.execute(
                "SELECT * FROM shot_characters WHERE shot_id=? ORDER BY position_order,id", (shot_id,)
            ).fetchall()
        return [
            ShotCharacterLink(
                id=row["id"], shot_id=row["shot_id"], character_id=row["character_id"], position_order=row["position_order"],
                action=row["action"], emotion=row["emotion"], dialogue=row["dialogue"], pose=row["pose"],
                expression_override=row["expression_override"], is_speaking=bool(row["is_speaking"]),
                voice_audio_asset_id=row["voice_audio_asset_id"], extra_data=json.loads(row["extra_data_json"] or "{}"),
            ) for row in rows
        ]

    def set_location(self, shot_id: str, location_id: str, *, time_of_day: str | None = None,
                     weather: str | None = None, atmosphere: str | None = None) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("DELETE FROM shot_locations WHERE shot_id=?", (shot_id,))
            self.store.connection.execute(
                "INSERT INTO shot_locations(id,shot_id,location_id,time_of_day_override,weather_override,atmosphere_override,created_at) VALUES(?,?,?,?,?,?,?)",
                (f"shotloc_{__import__('uuid').uuid4().hex}", shot_id, location_id, time_of_day, weather, atmosphere, _now()),
            )

    def get_location(self, shot_id: str) -> sqlite3.Row | None:
        with self.store._lock:
            return self.store.connection.execute("SELECT * FROM shot_locations WHERE shot_id=?", (shot_id,)).fetchone()

    def set_voice_audio_asset(self, link_id: str, asset_id: str) -> None:
        with self.store._lock, self.store.connection:
            cur = self.store.connection.execute(
                "UPDATE shot_characters SET voice_audio_asset_id=? WHERE id=?",
                (asset_id, link_id),
            )
            if cur.rowcount != 1:
                raise KeyError("SHOT_CHARACTER_LINK_NOT_FOUND")

    def update_generation(self, shot_id: str, *, prompt: str | None = None, negative_prompt: str | None = None,
                          status: str | None = None, error: str | None = None, image_asset_id: str | None = None,
                          continuity_hash: str | None = None, camera_angle: str | None = None, mood: str | None = None,
                          visual_style: dict[str, Any] | None = None) -> None:
        fields: list[str] = []
        values: list[Any] = []
        mapping = {
            "prompt": prompt, "generated_negative_prompt": negative_prompt, "generation_status": status,
            "generation_error": error, "generated_image_asset_id": image_asset_id, "continuity_hash": continuity_hash,
            "camera_angle": camera_angle, "mood": mood,
        }
        for column, value in mapping.items():
            if value is not None:
                fields.append(f"{column}=?")
                values.append(value)
        if visual_style is not None:
            fields.append("visual_style_json=?")
            values.append(json.dumps(visual_style, ensure_ascii=False))
        if not fields:
            return
        values.append(shot_id)
        with self.store._lock, self.store.connection:
            cur = self.store.connection.execute(f"UPDATE shots SET {','.join(fields)} WHERE id=?", tuple(values))
            if cur.rowcount != 1:
                raise KeyError("SHOT_NOT_FOUND")
