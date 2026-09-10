package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProjectEnvelope(val data: ProjectDto, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class ProjectDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val settings: Map<String, Any?> = emptyMap(),
    val createdAt: String? = null,
    val updatedAt: String? = null,
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
data class BackendJob(
    val id: String,
    val parentJobId: String? = null,
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String? = null,
    val priority: Int = 100,
    val status: String,
    val progress: Double = 0.0,
    val attempt: Int = 0,
    val maxAttempts: Int = 3,
    val provider: String? = null,
    val model: String? = null,
    val errorCode: String? = null,
    val errorMessage: String? = null,
    val createdAt: String? = null,
    val startedAt: String? = null,
    val completedAt: String? = null,
    val updatedAt: String? = null,
)

@JsonClass(generateAdapter = true)
data class JobEnvelope(val data: BackendJob, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class JobsMeta(val count: Int, val limit: Int)

@JsonClass(generateAdapter = true)
data class JobsFeed(val data: List<BackendJob>, val meta: JobsMeta, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class HealthData(val status: String, val service: String)

@JsonClass(generateAdapter = true)
data class HealthResponse(val data: HealthData, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class WorkerData(
    val workerId: String,
    val running: Boolean,
    val autostart: Boolean = false,
    val iterations: Int = 0,
    val lastError: String? = null,
)

@JsonClass(generateAdapter = true)
data class WorkerResponse(val data: WorkerData, val requestId: String? = null)
