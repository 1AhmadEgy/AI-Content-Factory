from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable


def canonical_fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_production_context(
    episode_snapshot: dict[str, Any],
    *,
    country_id: str,
    library_id: str,
    source_language: str,
    target_languages: Iterable[str] = (),
    dialect: str | None = None,
    glossary: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not country_id or not library_id or not source_language:
        raise ValueError("PRODUCTION_CONTEXT_SCOPE_REQUIRED")
    snapshot = deepcopy(episode_snapshot)
    snapshot_country = str(snapshot.get("countryId") or country_id)
    snapshot_library = str(snapshot.get("libraryId") or library_id)
    if snapshot_country != country_id or snapshot_library != library_id:
        raise ValueError("PRODUCTION_CONTEXT_SCOPE_MISMATCH")
    targets = list(dict.fromkeys(str(x) for x in target_languages if str(x).strip()))
    return {
        "schemaVersion": 1,
        "episodeId": str(snapshot.get("episodeId") or snapshot.get("episodeNumber") or "episode"),
        "countryId": country_id,
        "libraryId": library_id,
        "sourceLanguage": source_language,
        "targetLanguages": targets,
        "sourceVersion": int(snapshot.get("contextVersion") or snapshot.get("version") or 1),
        "dialect": dialect,
        "glossary": dict(glossary or {}),
        "sourceImmutable": True,
        "neverOverwriteUserChanges": True,
        "episodeSnapshot": snapshot,
        "sourceFingerprint": canonical_fingerprint(snapshot),
    }


def merge_production_context(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Fill missing production fields without replacing established user/source data."""
    result = deepcopy(base)
    for key, value in incoming.items():
        if key in {"episodeSnapshot", "sourceFingerprint"}:
            continue
        if key not in result or result[key] in (None, "", [], {}):
            result[key] = deepcopy(value)
    return result
