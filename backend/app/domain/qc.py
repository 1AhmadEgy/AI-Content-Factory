from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QcSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKER = "BLOCKER"


class QcCategory(str, Enum):
    INTEGRITY = "INTEGRITY"
    TECHNICAL = "TECHNICAL"
    MEDIA = "MEDIA"
    CONTINUITY = "CONTINUITY"
    SEMANTIC = "SEMANTIC"
    LICENSE = "LICENSE"


@dataclass(slots=True)
class QcFinding:
    category: QcCategory
    severity: QcSeverity
    code: str
    message: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QcResult:
    asset_id: str
    passed: bool
    score: float
    findings: list[QcFinding] = field(default_factory=list)
    evaluator: str = "deterministic"

    @property
    def blocked(self) -> bool:
        return any(f.severity == QcSeverity.BLOCKER for f in self.findings)


def evaluate_asset(
    *,
    asset_id: str,
    readable: bool,
    size_bytes: int,
    license_status: str,
    required_mime: str | None = None,
    actual_mime: str | None = None,
) -> QcResult:
    findings: list[QcFinding] = []
    score = 1.0

    if not readable or size_bytes <= 0:
        findings.append(QcFinding(QcCategory.INTEGRITY, QcSeverity.BLOCKER, "ASSET_UNREADABLE", "Asset is missing, empty, or unreadable."))
        score = 0.0

    if required_mime and actual_mime and required_mime != actual_mime:
        findings.append(QcFinding(QcCategory.TECHNICAL, QcSeverity.ERROR, "MIME_MISMATCH", "Asset MIME type does not match the required type."))
        score = min(score, 0.4)

    if license_status in {"BLOCKED", "RESTRICTED"}:
        findings.append(QcFinding(QcCategory.LICENSE, QcSeverity.BLOCKER, "LICENSE_BLOCKED", "Asset license status prevents production use."))
        score = 0.0
    elif license_status == "UNKNOWN":
        findings.append(QcFinding(QcCategory.LICENSE, QcSeverity.WARNING, "LICENSE_UNKNOWN", "Asset license has not been verified."))
        score = min(score, 0.8)

    passed = not any(f.severity in {QcSeverity.ERROR, QcSeverity.BLOCKER} for f in findings)
    return QcResult(asset_id=asset_id, passed=passed, score=score, findings=findings)
