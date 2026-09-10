package com.example.core.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import java.util.UUID

enum class JobStatus {
    CREATED, QUEUED, RUNNING, PAUSED, RETRYING, COMPLETED, FAILED, CANCELLED
}

@Entity(tableName = "projects")
@JsonClass(generateAdapter = true)
data class Project(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), val name: String, val description: String? = null,
    val mode: String = "MOCK", val status: String = "ACTIVE"
)

@Entity(tableName = "series")
@JsonClass(generateAdapter = true)
data class Series(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "project_id") val projectId: String,
    val title: String, val genre: String? = null, val language: String = "ar",
    @Json(name = "style_bible") val styleBible: Map<String, String> = emptyMap()
)

@Entity(tableName = "episodes")
@JsonClass(generateAdapter = true)
data class Episode(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "series_id") val seriesId: String,
    val number: Int, val title: String, val synopsis: String? = null, var status: String = "DRAFT"
)

@Entity(tableName = "scenes")
@JsonClass(generateAdapter = true)
data class Scene(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "episode_id") val episodeId: String,
    val number: Int, val description: String, val location: String? = null, val emotion: String? = null,
    var status: String = "PLANNED"
)

@Entity(tableName = "characters")
@JsonClass(generateAdapter = true)
data class Character(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "project_id") val projectId: String,
    val name: String, val description: String? = null, val age: String? = null, val gender: String? = null,
    val appearance: String? = null, val personality: String? = null, @Json(name = "voice_profile") val voiceProfile: String? = null,
    @Json(name = "reference_images") val referenceImages: String? = null, @Json(name = "negative_constraints") val negativeConstraints: String? = null
)

@Entity(tableName = "locations")
@JsonClass(generateAdapter = true)
data class Location(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "project_id") val projectId: String,
    val name: String, val description: String? = null, val lighting: String? = null,
    @Json(name = "color_palette") val colorPalette: String? = null, @Json(name = "reference_images") val referenceImages: String? = null
)

@Entity(tableName = "shots")
@JsonClass(generateAdapter = true)
data class Shot(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "scene_id") val sceneId: String,
    val number: Int, val camera: String? = null, val framing: String? = null, val movement: String? = null,
    val action: String? = null, val dialogue: String? = null, val duration: Int? = null, var status: String = "PLANNED"
)

@Entity(tableName = "jobs")
@JsonClass(generateAdapter = true)
data class GenerationJob(
    @PrimaryKey val id: String = UUID.randomUUID().toString(), @Json(name = "job_type") val jobType: String,
    @Json(name = "target_type") val targetType: String, @Json(name = "target_id") val targetId: String? = null,
    var status: JobStatus = JobStatus.QUEUED, var priority: Int = 50, var attempt: Int = 0,
    @Json(name = "max_attempts") val maxAttempts: Int = 3, val provider: String? = null, val model: String? = null,
    val input: String? = null, val output: String? = null, var progress: Int = 0, val error: String? = null,
    @Json(name = "errorCode") val errorCode: String? = null, @Json(name = "errorMessage") val errorMessage: String? = null,
    @Json(name = "created_at") val createdAt: Long = System.currentTimeMillis(), @Json(name = "started_at") var startedAt: Long? = null,
    @Json(name = "completed_at") var completedAt: Long? = null, @Json(name = "retry_policy") val retryPolicy: String? = "exponential",
    @Json(name = "fallback_provider") val fallbackProvider: String? = null
)

@JsonClass(generateAdapter = true)
data class JobsFeed(@Json(name = "data") val data: List<GenerationJob>, val meta: Map<String, Any?> = emptyMap())

@JsonClass(generateAdapter = true)
data class JobEnvelope(@Json(name = "data") val data: GenerationJob)

// API Request Models
@JsonClass(generateAdapter = true)
data class ProjectCreateRequest(val name: String, val description: String? = null, val mode: String = "MOCK")
@JsonClass(generateAdapter = true)
data class SeriesCreateRequest(@Json(name = "project_id") val projectId: String, val title: String, val genre: String? = null, val language: String = "ar")
@JsonClass(generateAdapter = true)
data class EpisodeCreateRequest(@Json(name = "series_id") val seriesId: String, val number: Int, val title: String, val synopsis: String? = null)
@JsonClass(generateAdapter = true)
data class SceneCreateRequest(@Json(name = "episode_id") val episodeId: String, val number: Int, val description: String, val location: String? = null, val emotion: String? = null)
