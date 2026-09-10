package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class CountryLibrariesEnvelope(val data: List<CountryLibrary>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CountryLibraryEnvelope(val data: CountryLibrary, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CountryLibrary(
    val id: String,
    val name: String,
    val nativeName: String,
    val countryCode: String,
    val locale: String,
    val defaultLanguage: String,
    val dialects: List<String> = emptyList(),
    val supportedLanguages: List<String> = emptyList(),
    val libraryId: String,
    val status: String,
    val libraryVersion: Int = 1,
    val contentCounts: Map<String, Int> = emptyMap(),
    val seriesTemplateCount: Int = 0,
)

@JsonClass(generateAdapter = true)
data class CountryLibraryContentEnvelope(val data: CountryLibraryContent, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CountryLibraryContent(
    val schemaVersion: Int = 1,
    val countryId: String,
    val libraryId: String,
    val name: String,
    val nativeName: String,
    val countryCode: String,
    val locale: String,
    val defaultLanguage: String,
    val dialects: List<String> = emptyList(),
    val status: String,
    val reusable: Boolean = true,
    val independent: Boolean = true,
    val nonDestructive: Boolean = true,
    val categories: List<String> = emptyList(),
    val seriesTemplates: List<String> = emptyList(),
    val contentCounts: Map<String, Int> = emptyMap(),
    val seedSource: List<String> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class LanguagesEnvelope(val data: List<LanguageInfo>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class LanguageEnvelope(val data: LanguageInfo, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class LanguageInfo(
    val id: String,
    val name: String,
    val nativeName: String? = null,
    val locales: List<String> = emptyList(),
    val rtl: Boolean = false,
)
