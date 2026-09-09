from backend.app.domain.best_take import TakeCandidate, select_best_take
from backend.app.domain.qc import QcCategory, QcSeverity, QcResult, evaluate_asset


def test_qc_accepts_readable_asset_with_unknown_license_as_warning():
    result = evaluate_asset(
        asset_id="a1",
        readable=True,
        size_bytes=10,
        license_status="UNKNOWN",
    )
    assert result.passed is True
    assert result.score == 0.8
    assert result.findings[0].severity == QcSeverity.WARNING
    assert result.findings[0].category == QcCategory.LICENSE


def test_qc_blocks_restricted_license():
    result = evaluate_asset(
        asset_id="a1",
        readable=True,
        size_bytes=10,
        license_status="RESTRICTED",
    )
    assert result.passed is False
    assert result.blocked is True


def test_best_take_ignores_failed_qc_and_uses_weighted_score():
    qc = {
        "a1": QcResult(asset_id="a1", passed=True, score=0.8),
        "a2": QcResult(asset_id="a2", passed=True, score=1.0),
        "bad": QcResult(asset_id="bad", passed=False, score=1.0),
    }
    winner = select_best_take(
        [
            TakeCandidate("a1", 0.8, semantic_score=1.0, continuity_score=1.0, technical_score=1.0),
            TakeCandidate("a2", 1.0, semantic_score=0.5, continuity_score=0.5, technical_score=0.5),
            TakeCandidate("bad", 1.0, semantic_score=1.0, continuity_score=1.0, technical_score=1.0),
        ],
        qc,
    )
    assert winner is not None
    assert winner.asset_id == "a1"
