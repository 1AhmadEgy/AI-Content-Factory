from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AssetType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    SUBTITLE = "SUBTITLE"
    THUMBNAIL = "THUMBNAIL"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


class AssetStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    CORRUPTED = "CORRUPTED"
    DELETED = "DELETED"


class LicenseStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    RESTRICTED = "RESTRICTED"
    BLOCKED = "BLOCKED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class AssetProvenance:
    provider: str | None = None
    model: str | None = None
    prompt: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    source_asset_ids: list[str] = field(default_factory=list)
    job_id: str | None = None
    license_status: LicenseStatus = LicenseStatus.UNKNOWN
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Asset:
    id: str
    project_id: str
    type: AssetType
    path: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: AssetStatus = AssetStatus.PENDING
    provenance: AssetProvenance = field(default_factory=AssetProvenance)
    created_at: datetime = field(default_factory=utc_now)
