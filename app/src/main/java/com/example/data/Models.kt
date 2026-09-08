package com.example.data

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import java.util.UUID

enum class JobStatus {
    QUEUED, RUNNING, COMPLETED, FAILED
}

@JsonClass(generateAdapter = true)
data class Project(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val description: String? = null,
    val mode: String = "MOCK",
    val status: String = "ACTIVE"
)

@JsonClass(generateAdapter = true)
data class Series(
    val id: String = UUID.randomUUID().toString(),
    @Json(name = "project_id") val projectId: String,
    val title: String,
    val genre: String? = null,
    val language: String = "ar",
    @Json(name = "style_bible") val styleBible: Map<String, String> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class Episode(
    val id: String = UUID.randomUUID().toString(),
    @Json(name = "series_id") val seriesId: String,
    val number: Int,
    val title: String,
    val synopsis: String? = null,
    var status: String = "DRAFT"
)

@JsonClass(generateAdapter = true)
data class Scene(
    val id: String = UUID.randomUUID().toString(),
    @Json(name = "episode_id") val episodeId: String,
    val number: Int,
    val description: String,
    val location: String? = null,
    val emotion: String? = null,
    var status: String = "PLANNED"
)

@JsonClass(generateAdapter = true)
data class GenerationJob(
    val id: String = UUID.randomUUID().toString(),
    @Json(name = "job_type") val jobType: String,
    @Json(name = "target_type") val targetType: String,
    @Json(name = "target_id") val targetId: String,
    var status: JobStatus = JobStatus.QUEUED,
    var progress: Int = 0,
    val provider: String? = null,
    val error: String? = null
)

// API Request Models
@JsonClass(generateAdapter = true)
data class ProjectCreateRequest(
    val name: String,
    val description: String? = null,
    val mode: String = "MOCK"
)

@JsonClass(generateAdapter = true)
data class SeriesCreateRequest(
    @Json(name = "project_id") val projectId: String,
    val title: String,
    val genre: String? = null,
    val language: String = "ar"
)

@JsonClass(generateAdapter = true)
data class EpisodeCreateRequest(
    @Json(name = "series_id") val seriesId: String,
    val number: Int,
    val title: String,
    val synopsis: String? = null
)

@JsonClass(generateAdapter = true)
data class SceneCreateRequest(
    @Json(name = "episode_id") val episodeId: String,
    val number: Int,
    val description: String,
    val location: String? = null,
    val emotion: String? = null
)
