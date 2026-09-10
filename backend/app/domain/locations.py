from __future__

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(frozen=True, slots=True)
class LocationProfile:
    id: str
    project_id: str
    name: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    geography: dict[str, Any] = field(default_factory=dict)
    architecture: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    visual_style: dict[str, Any] = field(default_factory=dict)
    lighting: dict[str, Any] = field(default_factory=dict)
    weather: dict[str, Any] = field(default_factory=dict)
    time_of_day: str | None = None
    props: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    reference_asset_ids: tuple[str, ...] = ()
    provider_location_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def snapshot(self) -> dict[str, Any]:
        return {"id": self.id, "projectId": self.project_id, "name": self.name, "aliases": list(self.aliases), "description": self.description, "geography": self.geography, "architecture": self.architecture, "environment": self.environment, "visualStyle": self.visual_style, "lighting": self.lighting, "weather": self.weather, "timeOfDay": self.time_of_day, "props": list(self.props), "rules": list(self.rules), "negativeConstraints": list(self.negative_constraints), "referenceAssetIds": list(self.reference_asset_ids), "providerLocationId": self.provider_location_id, "metadata": self.metadata, "version": self.version}
