package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SeriesTemplateEnvelope(val data: SeriesTemplate, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesTemplatesEnvelope(val data: List<SeriesTemplate>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesTemplate(val id: String, val name: String, val genre: String, val format: String, val tone: List<String> = emptyList(), val language: String? = null, val dialect: String? = null, val episode: Map<String, Any?> = emptyMap(), val continuity: Map<String, Any?> = emptyMap(), val storyRules: List<String> = emptyList(), val visual: Map<String, Any?> = emptyMap(), val audio: Map<String, Any?> = emptyMap(), val defaults: SeriesDefaults = SeriesDefaults())

@JsonClass(generateAdapter = true)
data class SeriesDefaults(val characterIds: List<String> = emptyList(), val locationIds: List<String> = emptyList())

@JsonClass(generateAdapter = true)
data class ApplySeriesTemplateRequest(val templateId: String, val title: String? = null, val countryId: String = "egypt", val sourceLanguage: String? = null, val targetLanguages: List<String> = emptyList(), val dialect: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesContextEnvelope(val data: SeriesContext, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesContext(val contextVersion: Int = 1, val seriesId: String, val title: String, val templateId: String, val genre: String, val nextEpisodeNumber: Int = 1, val characters: List<String> = emptyList(), val locations: List<String> = emptyList(), val relationships: List<Map<String, Any?>> = emptyList(), val facts: List<Map<String, Any?>> = emptyList(), val runningGags: List<Map<String, Any?>> = emptyList(), val openThreads: List<Map<String, Any?>> = emptyList(), val importantProps: List<Map<String, Any?>> = emptyList(), val timeline: List<Map<String, Any?>> = emptyList(), val episodeSnapshots: List<Map<String, Any?>> = emptyList(), val rules: Map<String, Any?> = emptyMap(), val branding: Map<String, Any?> = emptyMap(), val countryId: String? = null, val libraryId: String? = null, val sourceLanguage: String? = null, val targetLanguages: List<String> = emptyList(), val dialect: String? = null, val translationPolicy: Map<String, Any?> = emptyMap(), val glossary: Map<String, String> = emptyMap(), val translationVersions: Map<String, Any?> = emptyMap(), val updatedAt: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesContextPatchRequest(val context: Map<String, Any?>)

@JsonClass(generateAdapter = true)
data class EpisodeSnapshotEnvelope(val data: Map<String, Any?>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class SeriesSnapshotsEnvelope(val data: List<Map<String, Any?>>)
