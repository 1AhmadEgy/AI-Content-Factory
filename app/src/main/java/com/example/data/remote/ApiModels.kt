package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ApiEnvelope<T>(val data: T, val requestId: String)

@JsonClass(generateAdapter = true)
data class ProjectCreateRequest(
    val name: String
)

@JsonClass(generateAdapter = true)
data class ProjectDto(
    val id: String,
    val name: String,
    val createdAt: String,
    val updatedAt: String
)

@JsonClass(generateAdapter = true)
data class JobDto(
    val id: String,
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String?,
    val priority: Int,
    val status: String,
    val progress: Double,
    val attempt: Int,
    val maxAttempts: Int,
    val provider: String?,
    val model: String?,
    val input: Map<String, Any?>? = null,
    val output: Map<String, Any?>? = null,
    val errorCode: String?,
    val errorMessage: String?,
    val createdAt: String,
    val startedAt: String?,
    val completedAt: String?,
    val updatedAt: String
)

@JsonClass(generateAdapter = true)
data class JobInputDto(
    val schemaVersion: String = "1.0",
    val parameters: Map<String, Any?> = emptyMap(),
    val referenceAssetIds: List<String> = emptyList(),
    val constraints: Map<String, Any?> = emptyMap(),
    val seed: Long? = null,
    val deterministic: Boolean = false
)

@JsonClass(generateAdapter = true)
data class CreateJobRequest(
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String,
    val priority: Int = 50,
    val maxAttempts: Int = 3,
    val provider: String? = "mock",
    val model: String? = null,
    val input: JobInputDto = JobInputDto()
)
