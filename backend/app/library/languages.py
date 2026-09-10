from __future__ import annotations

"""Language and locale catalog shared by country libraries and translation."""

LANGUAGES: tuple[dict[str, object], ...] = (
    {"id": "ar", "name": "Arabic", "nativeName": "العربية", "locales": ["ar"], "rtl": True},
    {"id": "en", "name": "English", "nativeName": "English", "locales": ["en-US", "en-GB"], "rtl": False},
    {"id": "fr", "name": "French", "nativeName": "Français", "locales": ["fr-FR"], "rtl": False},
    {"id": "es", "name": "Spanish", "nativeName": "Español", "locales": ["es-ES", "es-MX"], "rtl": False},
    {"id": "de", "name": "German", "nativeName": "Deutsch", "locales": ["de-DE"], "rtl": False},
    {"id": "tr", "name": "Turkish", "nativeName": "Türkçe", "locales": ["tr-TR"], "rtl": False},
    {"id": "it", "name": "Italian", "nativeName": "Italiano", "locales": ["it-IT"], "rtl": False},
    {"id": "pt", "name": "Portuguese", "nativeName": "Português", "locales": ["pt-BR", "pt-PT"], "rtl": False},
    {"id": "ru", "name": "Russian", "nativeName": "Русский", "locales": ["ru-RU"], "rtl": False},
    {"id": "ja", "name": "Japanese", "nativeName": "日本語", "locales": ["ja-JP"], "rtl": False},
    {"id": "ko", "name": "Korean", "nativeName": "한국어", "locales": ["ko-KR"], "rtl": False},
    {"id": "zh", "name": "Chinese", "nativeName": "中文", "locales": ["zh-CN", "zh-TW"], "rtl": False},
)

LANGUAGE_BY_ID = {item["id"]: item for item in LANGUAGES}


def list_languages() -> list[dict[str, object]]:
    return [dict(item) for item in LANGUAGES]


def get_language(language_id: str) -> dict[str, object] | None:
    value = LANGUAGE_BY_ID.get(language_id)
    return dict(value) if value else None
