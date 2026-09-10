from __future__ import annotations

from copy import deepcopy


# Reusable series presets. They are defaults only: applying a preset merges missing
# values and never replaces project-specific settings.
SERIES_TEMPLATES: dict[str, dict] = {
    "comedy-series": {
        "id": "comedy-series", "name": "مسلسل كوميدي", "genre": "comedy",
        "format": "episodic-series", "tone": ["light", "warm", "fast-paced"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 600, "scenes": 10, "beats": ["setup", "escalation", "comic payoff"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveRelationships": True, "preserveRunningGags": True, "allowNewCharacters": True},
        "storyRules": ["Keep humor character-driven.", "Do not silently change a recurring character's core personality.", "Carry unresolved relationships and running jokes into later episodes."],
        "visual": {"style": "cinematic comedy", "camera": "energetic but readable", "lighting": "natural and warm"},
        "audio": {"dialoguePriority": "high", "music": "light comedic underscore", "sfx": "story-motivated"},
        "defaults": {"characterIds": ["char-egypt-felfel", "char-egypt-basbousa", "char-egypt-shokry"], "locationIds": ["loc-egypt-cafe", "loc-egypt-cairo-alley", "loc-egypt-nile-corniche"]},
    },
    "action-series": {
        "id": "action-series", "name": "مسلسل أكشن", "genre": "action",
        "format": "episodic-series", "tone": ["tense", "cinematic", "propulsive"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 900, "scenes": 14, "beats": ["mission", "complication", "confrontation", "cliffhanger"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveRelationships": True, "trackInjuries": True, "trackProps": True, "allowNewCharacters": True},
        "storyRules": ["Keep action grounded and spatially coherent.", "Track injuries, vehicles and important objects across scenes.", "Do not silently reset consequences between episodes."],
        "visual": {"style": "cinematic action realism", "camera": "dynamic with continuity-safe geography", "lighting": "motivated practical lighting"},
        "audio": {"dialoguePriority": "high", "music": "tension-driven score", "sfx": "precise action and environment"},
        "defaults": {"characterIds": ["char-egypt-tiger", "char-egypt-falcon", "char-egypt-shadow"], "locationIds": ["loc-egypt-cairo-alley", "loc-egypt-cairo-citadel", "loc-egypt-ramses-station"]},
    },
    "drama-series": {
        "id": "drama-series", "name": "مسلسل درامي", "genre": "drama",
        "format": "episodic-series", "tone": ["emotional", "grounded", "character-driven"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 1200, "scenes": 16, "beats": ["setup", "emotional turn", "conflict", "reveal"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveRelationships": True, "trackEmotionalArcs": True, "allowNewCharacters": True},
        "storyRules": ["Preserve emotional consequences between episodes.", "Keep family and relationship histories consistent.", "Prefer motivated changes over abrupt personality changes."],
        "visual": {"style": "natural cinematic drama", "camera": "intimate character coverage", "lighting": "motivated realistic"},
        "audio": {"dialoguePriority": "very-high", "music": "subtle emotional score", "sfx": "naturalistic"},
        "defaults": {"characterIds": ["char-egypt-zainab", "char-egypt-morwan"], "locationIds": ["loc-egypt-old-cairo", "loc-egypt-rural-village", "loc-egypt-cafe"]},
    },
    "mystery-series": {
        "id": "mystery-series", "name": "مسلسل تحقيق وغموض", "genre": "mystery",
        "format": "episodic-series", "tone": ["mysterious", "tense", "intelligent"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 900, "scenes": 14, "beats": ["case", "clue", "false lead", "reveal", "new question"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "trackClues": True, "trackSuspects": True, "trackEvidence": True, "allowNewCharacters": True},
        "storyRules": ["Every important clue must have a traceable origin.", "Do not reveal the solution earlier unless intentionally foreshadowed.", "Preserve case facts across episodes."],
        "visual": {"style": "cinematic mystery", "camera": "observational and controlled", "lighting": "motivated contrast"},
        "audio": {"dialoguePriority": "very-high", "music": "minimal suspense", "sfx": "detailed environment"},
        "defaults": {"characterIds": ["char-egypt-younes", "char-egypt-adil"], "locationIds": ["loc-egypt-police-station-fictional", "loc-egypt-cairo-alley", "loc-egypt-khan-el-khalili"]},
    },
    "adventure-series": {
        "id": "adventure-series", "name": "مسلسل مغامرات", "genre": "adventure",
        "format": "episodic-series", "tone": ["adventurous", "wonder", "family-friendly"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 900, "scenes": 12, "beats": ["discovery", "journey", "obstacle", "reward", "hook"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "trackMapProgress": True, "trackProps": True, "allowNewCharacters": True},
        "storyRules": ["Track journey geography and important objects.", "Keep discoveries consistent with previous episodes.", "Make new locations distinct while preserving their identity."],
        "visual": {"style": "cinematic adventure", "camera": "wide establishing shots plus character coverage", "lighting": "location-motivated"},
        "audio": {"dialoguePriority": "high", "music": "adventure score", "sfx": "environment-rich"},
        "defaults": {"characterIds": ["char-egypt-marwan", "char-egypt-rami", "char-egypt-salma"], "locationIds": ["loc-egypt-saqquara", "loc-egypt-philae-temple", "loc-egypt-white-desert"]},
    },
    "family-series": {
        "id": "family-series", "name": "مسلسل عائلي", "genre": "family",
        "format": "episodic-series", "tone": ["warm", "funny", "heartfelt"],
        "language": "ar-EG", "dialect": "Egyptian Arabic",
        "episode": {"durationSeconds": 720, "scenes": 11, "beats": ["family problem", "misunderstanding", "teamwork", "resolution"]},
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveRelationships": True, "trackFamilyFacts": True, "allowNewCharacters": True},
        "storyRules": ["Protect family relationship continuity.", "Keep conflict suitable for the selected audience rating.", "Carry routines and recurring jokes forward naturally."],
        "visual": {"style": "warm cinematic family", "camera": "clear ensemble coverage", "lighting": "soft natural and practical"},
        "audio": {"dialoguePriority": "very-high", "music": "warm light score", "sfx": "natural home and street sounds"},
        "defaults": {"characterIds": ["char-egypt-omar", "char-egypt-mariam", "char-egypt-hag-mahmoud"], "locationIds": ["loc-egypt-cairo-alley", "loc-egypt-rural-village", "loc-egypt-cafe"]},
    },
}


def list_series_templates() -> list[dict]:
    return [deepcopy(value) for value in SERIES_TEMPLATES.values()]


def get_series_template(template_id: str) -> dict | None:
    value = SERIES_TEMPLATES.get(template_id)
    return deepcopy(value) if value else None


def merge_missing(base: dict, defaults: dict) -> dict:
    """Deep-merge defaults without overwriting user-owned values."""
    result = deepcopy(base)
    for key, value in defaults.items():
        if key not in result:
            result[key] = deepcopy(value)
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_missing(result[key], value)
    return result
