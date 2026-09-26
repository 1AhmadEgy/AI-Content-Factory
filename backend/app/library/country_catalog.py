"""Scalable country-library registry.

A country entry is metadata until a content seed is provided. Each country has
an independent stable libraryId, so adding content never requires changing the
API contract or touching another country's records.
"""

from __future__ import annotations

from .languages import LANGUAGES

COMMON_LANGUAGES = tuple(item["id"] for item in LANGUAGES)

_COUNTRIES: tuple[dict[str, object], ...] = (
    {"id": "egypt", "name": "Egypt", "nativeName": "مصر", "countryCode": "EG", "locale": "ar-EG", "defaultLanguage": "ar", "dialects": ["ar-EG"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-egypt", "status": "ready", "libraryVersion": 1},
    {"id": "libya", "name": "Libya", "nativeName": "ليبيا", "countryCode": "LY", "locale": "ar-LY", "defaultLanguage": "ar", "dialects": ["ar-LY"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-libya", "status": "partial", "libraryVersion": 1},
    {"id": "saudi_arabia", "name": "Saudi Arabia", "nativeName": "السعودية", "countryCode": "SA", "locale": "ar-SA", "defaultLanguage": "ar", "dialects": ["ar-SA"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-saudi-arabia", "status": "catalog-only", "libraryVersion": 1},
    {"id": "uae", "name": "United Arab Emirates", "nativeName": "الإمارات العربية المتحدة", "countryCode": "AE", "locale": "ar-AE", "defaultLanguage": "ar", "dialects": ["ar-AE"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-uae", "status": "catalog-only", "libraryVersion": 1},
    {"id": "iraq", "name": "Iraq", "nativeName": "العراق", "countryCode": "IQ", "locale": "ar-IQ", "defaultLanguage": "ar", "dialects": ["ar-IQ"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-iraq", "status": "catalog-only", "libraryVersion": 1},
    {"id": "jordan", "name": "Jordan", "nativeName": "الأردن", "countryCode": "JO", "locale": "ar-JO", "defaultLanguage": "ar", "dialects": ["ar-JO"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-jordan", "status": "catalog-only", "libraryVersion": 1},
    {"id": "syria", "name": "Syria", "nativeName": "سوريا", "countryCode": "SY", "locale": "ar-SY", "defaultLanguage": "ar", "dialects": ["ar-SY"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-syria", "status": "catalog-only", "libraryVersion": 1},
    {"id": "morocco", "name": "Morocco", "nativeName": "المغرب", "countryCode": "MA", "locale": "ar-MA", "defaultLanguage": "ar", "dialects": ["ar-MA", "fr-MA"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-morocco", "status": "catalog-only", "libraryVersion": 1},
    {"id": "algeria", "name": "Algeria", "nativeName": "الجزائر", "countryCode": "DZ", "locale": "ar-DZ", "defaultLanguage": "ar", "dialects": ["ar-DZ", "fr-DZ"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-algeria", "status": "catalog-only", "libraryVersion": 1},
    {"id": "tunisia", "name": "Tunisia", "nativeName": "تونس", "countryCode": "TN", "locale": "ar-TN", "defaultLanguage": "ar", "dialects": ["ar-TN", "fr-TN"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-tunisia", "status": "catalog-only", "libraryVersion": 1},
    {"id": "turkey", "name": "Turkey", "nativeName": "Türkiye", "countryCode": "TR", "locale": "tr-TR", "defaultLanguage": "tr", "dialects": ["tr-TR"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-turkey", "status": "catalog-only", "libraryVersion": 1},
    {"id": "usa", "name": "United States", "nativeName": "United States", "countryCode": "US", "locale": "en-US", "defaultLanguage": "en", "dialects": ["en-US"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-usa", "status": "catalog-only", "libraryVersion": 1},
    {"id": "uk", "name": "United Kingdom", "nativeName": "United Kingdom", "countryCode": "GB", "locale": "en-GB", "defaultLanguage": "en", "dialects": ["en-GB"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-uk", "status": "catalog-only", "libraryVersion": 1},
    {"id": "france", "name": "France", "nativeName": "France", "countryCode": "FR", "locale": "fr-FR", "defaultLanguage": "fr", "dialects": ["fr-FR"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-france", "status": "catalog-only", "libraryVersion": 1},
    {"id": "japan", "name": "Japan", "nativeName": "日本", "countryCode": "JP", "locale": "ja-JP", "defaultLanguage": "ja", "dialects": ["ja-JP"], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-japan", "status": "catalog-only", "libraryVersion": 1},
    {"id": "global", "name": "Global", "nativeName": "Global", "countryCode": "XX", "locale": "en-US", "defaultLanguage": "en", "dialects": [], "supportedLanguages": list(COMMON_LANGUAGES), "libraryId": "local-library-global", "status": "catalog-only", "libraryVersion": 1},
)

COUNTRY_BY_ID = {item["id"]: item for item in _COUNTRIES}


def list_country_libraries() -> list[dict[str, object]]:
    return [dict(item) for item in _COUNTRIES]


def get_country_library(country_id: str) -> dict[str, object] | None:
    value = COUNTRY_BY_ID.get(country_id)
    return dict(value) if value else None


def get_country_languages(country_id: str) -> list[dict[str, object]]:
    country = COUNTRY_BY_ID.get(country_id)
    if country is None:
        return []
    allowed = set(country["supportedLanguages"])
    dialects = list(country.get("dialects", []))
    return [dict(item, locale=(item.get("locales") or [None])[0], dialects=dialects if item["id"] == country["defaultLanguage"] else list(item.get("locales", []))) for item in LANGUAGES if item["id"] in allowed]
