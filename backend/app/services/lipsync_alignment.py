from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping

from ..rendering.media_artifacts import SubtitleCue


class LipSyncAlignmentError(ValueError):
    """Raised when speech timing cannot safely enter production."""


@dataclass(frozen=True, slots=True)
class WordTiming:
    text: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0
    speaker: str | None = None
    shot_id: str | None = None

    def validate(self) -> None:
        if not self.text.strip():
            raise LipSyncAlignmentError("word text must not be empty")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise LipSyncAlignmentError("word timing range is invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise LipSyncAlignmentError("word confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    cues: tuple[SubtitleCue, ...]
    words: tuple[WordTiming, ...]
    duration_ms: int
    offset_ms: int = 0
    provenance: dict[str, Any] | None = None

    def validate(self) -> None:
        if self.duration_ms <= 0:
            raise LipSyncAlignmentError("duration_ms must be positive")
        previous_end = 0
        for word in self.words:
            word.validate()
            if word.start_ms < previous_end:
                raise LipSyncAlignmentError("word timings overlap or are out of order")
            previous_end = word.end_ms
        for cue in self.cues:
            if cue.start_ms < 0 or cue.end_ms <= cue.start_ms or cue.end_ms > self.duration_ms:
                raise LipSyncAlignmentError("subtitle cue is outside the media duration")


class LipSyncAlignmentEngine:
    """Normalize real ASR/TTS timings into stable subtitle and sync contracts."""

    def align_words(self, words: Iterable[Mapping[str, Any]], *, duration_ms: int, offset_ms: int = 0, minimum_confidence: float = 0.0, provenance: Mapping[str, Any] | None = None) -> AlignmentResult:
        if duration_ms <= 0:
            raise LipSyncAlignmentError("duration_ms must be positive")
        if not 0.0 <= minimum_confidence <= 1.0:
            raise LipSyncAlignmentError("minimum_confidence must be between 0 and 1")
        normalized: list[WordTiming] = []
        for raw in words:
            if not isinstance(raw, Mapping):
                raise LipSyncAlignmentError("word timing must be an object")
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            try:
                start = int(round(float(raw.get("start_ms", raw.get("start", 0))))) + offset_ms
                end = int(round(float(raw.get("end_ms", raw.get("end", 0))))) + offset_ms
                confidence = float(raw.get("confidence", 1.0))
            except (TypeError, ValueError) as exc:
                raise LipSyncAlignmentError("word timing contains non-numeric timestamps") from exc
            if confidence < minimum_confidence:
                continue
            word = WordTiming(text, start, end, confidence, self._optional(raw, "speaker"), self._optional(raw, "shot_id", "shotId"))
            word.validate()
            if end > duration_ms:
                raise LipSyncAlignmentError("word timing exceeds media duration")
            normalized.append(word)
        normalized.sort(key=lambda item: (item.start_ms, item.end_ms, item.text))
        cues = [SubtitleCue(word.start_ms, word.end_ms, word.text) for word in normalized]
        result = AlignmentResult(tuple(cues), tuple(normalized), duration_ms, offset_ms, dict(provenance or {}))
        result.validate()
        return result

    def build_subtitles(self, words: Iterable[Mapping[str, Any]], *, duration_ms: int, max_words: int = 8, max_duration_ms: int = 5000, offset_ms: int = 0, provenance: Mapping[str, Any] | None = None) -> AlignmentResult:
        if max_words < 1 or max_duration_ms < 1:
            raise LipSyncAlignmentError("subtitle grouping limits must be positive")
        result = self.align_words(words, duration_ms=duration_ms, offset_ms=offset_ms, provenance=provenance)
        grouped: list[SubtitleCue] = []
        bucket: list[WordTiming] = []
        for word in result.words:
            if bucket and (len(bucket) >= max_words or word.end_ms - bucket[0].start_ms > max_duration_ms):
                grouped.append(SubtitleCue(bucket[0].start_ms, bucket[-1].end_ms, " ".join(item.text for item in bucket)))
                bucket = []
            bucket.append(word)
        if bucket:
            grouped.append(SubtitleCue(bucket[0].start_ms, bucket[-1].end_ms, " ".join(item.text for item in bucket)))
        final = AlignmentResult(tuple(grouped), result.words, result.duration_ms, result.offset_ms, {**(result.provenance or {}), "subtitleGrouping": {"maxWords": max_words, "maxDurationMs": max_duration_ms}})
        final.validate()
        return final

    def sync_score(self, *, expected: Iterable[Mapping[str, Any]], observed: Iterable[Mapping[str, Any]], tolerance_ms: int = 120) -> dict[str, Any]:
        if tolerance_ms < 0:
            raise LipSyncAlignmentError("tolerance_ms must be non-negative")
        exp, obs = list(expected), list(observed)
        if not exp:
            raise LipSyncAlignmentError("expected timings are empty")
        if len(exp) != len(obs):
            return {"score": 0.0, "confidence": 1.0, "matched": 0, "expected": len(exp), "observed": len(obs), "withinTolerance": False}
        errors: list[int] = []
        matched = 0
        for left, right in zip(exp, obs):
            try:
                error = abs(int(left["start_ms"]) - int(right["start_ms"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise LipSyncAlignmentError("sync comparison requires start_ms") from exc
            errors.append(error)
            matched += error <= tolerance_ms
        mean_error = sum(errors) / len(errors)
        score = max(0.0, min(1.0, 1.0 - mean_error / max(tolerance_ms * 2, 1)))
        return {"score": score, "confidence": matched / len(errors), "matched": matched, "expected": len(exp), "observed": len(obs), "meanErrorMs": mean_error, "toleranceMs": tolerance_ms, "withinTolerance": matched == len(errors)}

    @staticmethod
    def _optional(raw: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = raw.get(key)
            if value is not None and str(value).strip():
                return str(value)
        return None

    @staticmethod
    def stable_alignment_id(result: AlignmentResult) -> str:
        payload = "|".join(f"{w.text}:{w.start_ms}:{w.end_ms}" for w in result.words)
        return sha256(payload.encode("utf-8")).hexdigest()[:20]
