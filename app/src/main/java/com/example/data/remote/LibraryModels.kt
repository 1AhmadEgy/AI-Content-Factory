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
)

@JsonClass(generateAdapter = true)
data class LanguagesEnvelope(val data: List<LanguageInfo>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class LanguageInfo(
    val id: String,
    val name: String,
    val nativeName: String? = null,
    val locale: String? = null,
    val dialects: List<String> = emptyList(),
)
