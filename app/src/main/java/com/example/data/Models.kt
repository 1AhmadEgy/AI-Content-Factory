package com.example.data

import java.util.UUID

enum class JobStatus {
    QUEUED, RUNNING, COMPLETED, FAILED
}

data class Project(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val description: String? = null,
    val mode: String = "MOCK",
    val status: String = "ACTIVE"
)

data class Series(
    val id: String = UUID.randomUUID().toString(),
    val projectId: String,
    val title: String,
    val genre: String? = null,
    val language: String = "ar",
    val styleBible: Map<String, String> = emptyMap()
)

data class Episode(
    val id: String = UUID.randomUUID().toString(),
    val seriesId: String,
    val number: Int,
    val title: String,
    val synopsis: String? = null,
    var status: String = "DRAFT"
)

data class Scene(
    val id: String = UUID.randomUUID().toString(),
    val episodeId: String,
    val number: Int,
    val description: String,
    val location: String? = null,
    val emotion: String? = null,
    var status: String = "PLANNED"
)

data class GenerationJob(
    val id: String = UUID.randomUUID().toString(),
    val jobType: String,
    val targetType: String,
    val targetId: String,
    var status: JobStatus = JobStatus.QUEUED,
    var progress: Int = 0,
    val provider: String? = null,
    val error: String? = null
)
