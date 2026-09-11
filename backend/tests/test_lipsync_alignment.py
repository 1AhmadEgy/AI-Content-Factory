import pytest

from app.services.lipsync_alignment import LipSyncAlignmentEngine, LipSyncAlignmentError


def test_align_words_applies_offset_and_preserves_provenance() -> None:
    result = LipSyncAlignmentEngine().align_words(
        [{"text": "Hello", "start_ms": 100, "end_ms": 500, "confidence": 0.99, "shotId": "shot-1"}, {"text": "world", "start_ms": 520, "end_ms": 900, "confidence": 0.95}],
        duration_ms=1500, offset_ms=50, provenance={"provider_id": "real-asr", "provider_run_id": "run-1"},
    )
    assert [(w.start_ms, w.end_ms) for w in result.words] == [(150, 550), (570, 950)]
    assert result.words[0].shot_id == "shot-1"
    assert result.provenance["provider_id"] == "real-asr"


def test_build_subtitles_groups_words_without_exceeding_limits() -> None:
    words = [{"text": "one", "start_ms": 0, "end_ms": 300}, {"text": "two", "start_ms": 320, "end_ms": 600}, {"text": "three", "start_ms": 620, "end_ms": 900}, {"text": "four", "start_ms": 920, "end_ms": 1200}]
    result = LipSyncAlignmentEngine().build_subtitles(words, duration_ms=2000, max_words=2, max_duration_ms=2000)
    assert [cue.text for cue in result.cues] == ["one two", "three four"]
    assert result.cues[0].start_ms == 0
    assert result.cues[0].end_ms == 600


def test_low_confidence_words_can_be_filtered() -> None:
    result = LipSyncAlignmentEngine().align_words(
        [{"text": "keep", "start_ms": 0, "end_ms": 300, "confidence": 0.9}, {"text": "drop", "start_ms": 400, "end_ms": 700, "confidence": 0.2}],
        duration_ms=1000, minimum_confidence=0.8,
    )
    assert [word.text for word in result.words] == ["keep"]


def test_sync_score_is_thresholded_and_deterministic() -> None:
    result = LipSyncAlignmentEngine().sync_score(expected=[{"start_ms": 100}, {"start_ms": 500}], observed=[{"start_ms": 130}, {"start_ms": 530}], tolerance_ms=50)
    assert result["withinTolerance"] is True
    assert result["score"] == 0.7
    assert result["confidence"] == 1.0


def test_invalid_timing_is_rejected_instead_of_clamped() -> None:
    with pytest.raises(LipSyncAlignmentError, match="exceeds media duration"):
        LipSyncAlignmentEngine().align_words([{"text": "late", "start_ms": 900, "end_ms": 1100}], duration_ms=1000)


def test_empty_expected_sync_is_rejected() -> None:
    with pytest.raises(LipSyncAlignmentError, match="expected timings are empty"):
        LipSyncAlignmentEngine().sync_score(expected=[], observed=[])
