from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReferenceStatus(str, Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CharacterReference:
    reference_id: str
    character_id: str
    asset_id: str
    status: ReferenceStatus = ReferenceStatus.CANDIDATE
    embedding: tuple[float, ...] | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.reference_id.strip():
            raise ValueError("reference_id must not be empty")
        if not self.character_id.strip():
            raise ValueError("character_id must not be empty")
        if not self.asset_id.strip():
            raise ValueError("asset_id must not be empty")
        if self.embedding is not None and not self.embedding:
            raise ValueError("embedding must not be empty when provided")
        if self.embedding is not None and any(not isinstance(value, (int, float)) for value in self.embedding):
            raise ValueError("embedding values must be numeric")


@dataclass(frozen=True, slots=True)
class CharacterAnchor:
    character_id: str
    reference_id: str
    reference_asset_id: str
    shot_id: str
    prompt: str
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for name, value in {
            "character_id": self.character_id,
            "reference_id": self.reference_id,
            "reference_asset_id": self.reference_asset_id,
            "shot_id": self.shot_id,
            "prompt": self.prompt,
        }.items():
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    reference_id: str
    candidate_asset_id: str
    score: float
    threshold: float
    passed: bool
    metric: str = "embedding-cosine"
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("similarity score must be between 0 and 1")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("similarity threshold must be between 0 and 1")
        if not self.reference_id.strip() or not self.candidate_asset_id.strip():
            raise ValueError("reference_id and candidate_asset_id must not be empty")
