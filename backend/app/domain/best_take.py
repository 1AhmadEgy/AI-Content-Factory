from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .qc import QcResult


@dataclass(frozen=True, slots=True)
class TakeCandidate:
    asset_id: str
    qc_score: float
    semantic_score: float = 0.0
    continuity_score: float = 0.0
    technical_score: float = 0.0

    @property
    def total_score(self) -> float:
        return (
            self.qc_score * 0.4
            + self.semantic_score * 0.25
            + self.continuity_score * 0.2
            + self.technical_score * 0.15
        )


def select_best_take(candidates: Iterable[TakeCandidate], qc_results: dict[str, QcResult]) -> TakeCandidate | None:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.asset_id in qc_results
        and qc_results[candidate.asset_id].passed
        and not qc_results[candidate.asset_id].blocked
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda candidate: (candidate.total_score, candidate.asset_id))
