from __future__ import annotations

from hashlib import sha256
from math import sqrt
from typing import Any, Callable, Mapping

from ..domain.character_consistency import CharacterAnchor, CharacterReference, ReferenceStatus, SimilarityResult
from ..domain.storyboard import Shot
from .series_bible import SeriesBibleService


class CharacterConsistencyError(ValueError):
    pass


EmbeddingProvider = Callable[[str], tuple[float, ...]]


class CharacterConsistencyService:
    """Canonical character references and provider-neutral shot anchoring.

    This service never fabricates media. It records references/assets supplied by
    real generation pipelines and produces deterministic anchor instructions and
    similarity QC. Embedding extraction remains an injectable provider boundary.
    """

    def __init__(self, bible: SeriesBibleService, *, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.bible = bible
        self.embedding_provider = embedding_provider

    def register_reference(
        self,
        project_id: str,
        *,
        character_id: str,
        asset_id: str,
        reference_id: str | None = None,
        status: ReferenceStatus = ReferenceStatus.CANDIDATE,
        embedding: tuple[float, ...] | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> CharacterReference:
        if not character_id.strip() or not asset_id.strip():
            raise CharacterConsistencyError("character_id and asset_id are required")
        reference_id = reference_id or self._stable_id("reference", project_id, character_id, asset_id)
        reference = CharacterReference(
            reference_id=reference_id,
            character_id=character_id,
            asset_id=asset_id,
            status=status,
            embedding=embedding,
            provenance=dict(provenance or {}),
        )
        reference.validate()
        payload = {
            "referenceId": reference.reference_id,
            "characterId": reference.character_id,
            "assetId": reference.asset_id,
            "status": reference.status.value,
            "embedding": list(reference.embedding) if reference.embedding is not None else None,
            "provenance": dict(reference.provenance),
        }
        self.bible.update_continuity(project_id, {
            "characterReferences": {
                **self.bible.snapshot(project_id).get("continuity", {}).get("characterReferences", {}),
                reference.reference_id: payload,
            }
        })
        self.bible.record_asset(project_id, asset_id, {
            "role": "character-reference",
            "characterId": character_id,
            "referenceId": reference.reference_id,
            "status": status.value,
            "provenance": dict(provenance or {}),
        })
        return reference

    def approve_master_reference(self, project_id: str, reference: CharacterReference) -> CharacterReference:
        reference.validate()
        if reference.status is ReferenceStatus.REJECTED:
            raise CharacterConsistencyError("a rejected reference cannot be approved")
        approved = CharacterReference(
            reference_id=reference.reference_id,
            character_id=reference.character_id,
            asset_id=reference.asset_id,
            status=ReferenceStatus.APPROVED,
            embedding=reference.embedding,
            provenance={**reference.provenance, "approved": True},
        )
        snapshot = self.bible.snapshot(project_id)
        refs = dict(snapshot.get("continuity", {}).get("characterReferences", {}))
        refs[approved.reference_id] = {
            **refs.get(approved.reference_id, {}),
            "referenceId": approved.reference_id,
            "characterId": approved.character_id,
            "assetId": approved.asset_id,
            "status": approved.status.value,
            "embedding": list(approved.embedding) if approved.embedding is not None else None,
            "provenance": dict(approved.provenance),
        }
        masters = dict(snapshot.get("continuity", {}).get("masterReferences", {}))
        masters[approved.character_id] = approved.reference_id
        self.bible.update_continuity(project_id, {"characterReferences": refs, "masterReferences": masters})
        return approved

    def master_reference(self, project_id: str, character_id: str) -> CharacterReference | None:
        continuity = self.bible.snapshot(project_id).get("continuity", {})
        reference_id = continuity.get("masterReferences", {}).get(character_id)
        if not reference_id:
            return None
        data = continuity.get("characterReferences", {}).get(reference_id)
        if not data or data.get("status") != ReferenceStatus.APPROVED.value:
            return None
        embedding = data.get("embedding")
        return CharacterReference(
            reference_id=str(data["referenceId"]),
            character_id=str(data["characterId"]),
            asset_id=str(data["assetId"]),
            status=ReferenceStatus.APPROVED,
            embedding=tuple(float(v) for v in embedding) if embedding is not None else None,
            provenance=dict(data.get("provenance") or {}),
        )

    def anchor_shot(self, project_id: str, shot: Shot) -> tuple[CharacterAnchor, ...]:
        anchors: list[CharacterAnchor] = []
        for character_id in shot.character_ids:
            reference = self.master_reference(project_id, character_id)
            if reference is None:
                raise CharacterConsistencyError(
                    f"No approved master reference exists for character={character_id!r}; "
                    "generate/approve a real reference before generating the shot."
                )
            anchor = CharacterAnchor(
                character_id=character_id,
                reference_id=reference.reference_id,
                reference_asset_id=reference.asset_id,
                shot_id=shot.shot_id,
                prompt=self._anchored_prompt(shot.prompt, character_id, reference),
                provenance={
                    "referenceId": reference.reference_id,
                    "referenceAssetId": reference.asset_id,
                    "source": "approved-master-reference",
                },
            )
            anchor.validate()
            anchors.append(anchor)
        return tuple(anchors)

    def check_similarity(
        self,
        reference: CharacterReference,
        *,
        candidate_asset_id: str,
        candidate_embedding: tuple[float, ...] | None = None,
        threshold: float = 0.82,
        metric: str = "embedding-cosine",
    ) -> SimilarityResult:
        reference.validate()
        if not candidate_asset_id.strip():
            raise CharacterConsistencyError("candidate_asset_id is required")
        if not 0.0 <= threshold <= 1.0:
            raise CharacterConsistencyError("threshold must be between 0 and 1")
        if reference.embedding is None:
            raise CharacterConsistencyError("master reference has no embedding; configure a real embedding provider")
        candidate = candidate_embedding
        if candidate is None:
            if self.embedding_provider is None:
                raise CharacterConsistencyError("candidate embedding is missing and no real embedding provider is configured")
            candidate = self.embedding_provider(candidate_asset_id)
        score = self._cosine_similarity(reference.embedding, candidate)
        result = SimilarityResult(
            reference_id=reference.reference_id,
            candidate_asset_id=candidate_asset_id,
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            metric=metric,
            provenance={"referenceAssetId": reference.asset_id},
        )
        result.validate()
        return result

    @staticmethod
    def _anchored_prompt(prompt: str, character_id: str, reference: CharacterReference) -> str:
        return (
            f"{prompt.strip()}\n\n"
            f"Character consistency anchor: preserve character {character_id} exactly from "
            f"approved reference asset {reference.asset_id} (reference {reference.reference_id}). "
            "Do not invent a replacement identity, costume, age, or facial structure."
        )

    @staticmethod
    def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right) or not left:
            raise CharacterConsistencyError("reference and candidate embeddings must have equal non-zero dimensions")
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            raise CharacterConsistencyError("embeddings must have non-zero magnitude")
        return max(0.0, min(1.0, (dot / (left_norm * right_norm) + 1.0) / 2.0))

    @staticmethod
    def _stable_id(*parts: str) -> str:
        return sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
