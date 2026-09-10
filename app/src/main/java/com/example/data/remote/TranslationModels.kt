package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class TranslationRequest(
    val sourceLanguage: String,
    val targetLanguage: String,
    val text: String,
    val contentType: String = "dialogue",
    val sourceId: String? = null,
    val sourceVersion: Int = 1,
    val preserveTerms: List<String> = emptyList(),
    val glossary: Map<String, String> = emptyMap(),
    val context: Map<String, Any?> = emptyMap(),
    val manualText: String? = null,
    val provider: String? = null,
    val model: String? = null,
    val version: Int = 1,
)

@JsonClass(generateAdapter = true)
data class TranslationBatchRequest(
    val sourceLanguage: String,
    val targetLanguages: List<String>,
    val text: String,
    val contentType: String = "dialogue",
    val sourceId: String? = null,
    val sourceVersion: Int = 1,
    val preserveTerms: List<String> = emptyList(),
    val glossary: Map<String, String> = emptyMap(),
    val context: Map<String, Any?> = emptyMap(),
    val provider: String? = null,
    val model: String? = null,
    val version: Int = 1,
    val manualTexts: Map<String, String> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class TranslationEnvelope(val data: Translation, val requestId: String? = null, val idempotent: Boolean = false)

@JsonClass(generateAdapter = true)
data class TranslationBatchEnvelope(val data: List<Translation> = emptyList(), val errors: List<Map<String, String>> = emptyList(), val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class TranslationsEnvelope(val data: List<Translation> = emptyList(), val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class Translation(
    val id: String,
    val sourceLanguage: String,
    val targetLanguage: String,
    val sourceText: String,
    val translatedText: String,
    val contentType: String,
    val sourceId: String? = null,
    val provider: String = "local",
    val model: String? = null,
    val glossaryVersion: Int = 1,
    val version: Int = 1,
    val manual: Boolean = false,
    val createdAt: String? = null,
    val metadata: Map<String, Any?> = emptyMap(),
)
