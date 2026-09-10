package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProjectEnvelope(val data: ProjectDto, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class ProjectDto(
    val id: String,
    val name: String,
    val description: String? = null,
)

@JsonClass(generateAdapter = true)
data class JobInputRequest(
    val parameters: Map<String, Any?> = emptyMap(),
    val referenceAssetIds: List<String> = emptyList(),
    val constraints: Map<String, Any?> = emptyMap(),
    val seed: Int? = null,
    val deterministic: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class CreateJobRequest(
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String? = null,
    val parentJobId: String? = null,
    val priority: Int = 100,
    val maxAttempts: Int = 3,
    val provider: String? = null,
    val model: String? = null,
    val input: JobInputRequest = JobInputRequest(),
)

@JsonClass(generateAdapter = true)
data class JobEnvelope(val data: BackendJob, val requestId: String? = null)
