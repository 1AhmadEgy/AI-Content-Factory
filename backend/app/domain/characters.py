from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class CharacterProfile:
    id: str
    project_id: str
    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    personality: dict[str, object] = field(default_factory=dict)
    appearance: dict[str, object] = field(default_factory=dict)
    voice: dict[str, object] = field(default_factory=dict)
    speaking_style: dict[str, object] = field(default_factory=dict)
    visual_style: dict[str, object] = field(default_factory=dict)
    behavior_rules: tuple[str, ...] = ()
    reference_asset_ids: tuple[str, ...] = ()
    provider_character_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id, "projectId": self.project_id, "name": self.name,
            "aliases": list(self.aliases), "description": self.description,
            "personality": self.personality, "appearance": self.appearance,
            "voice": self.voice, "speakingStyle": self.speaking_style,
            "visualStyle": self.visual_style, "behaviorRules": list(self.behavior_rules),
            "referenceAssetIds": list(self.reference_asset_ids),
            "providerCharacterId": self.provider_character_id, "metadata": self.metadata,
            "version": self.version,
        }
