package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BackendJob(
    val id: String,
    val parentJobId: String? = null,
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String?,
    val status: String,
    val progress: Double = 0.0,
    val attempt: Int = 0,
    val maxAttempts: Int = 3,
    val priority: Int = 100,
    val provider: String? = null,
    val model: String? = null,
    val errorCode: String? = null,
    val errorMessage: String? = null,
    val createdAt: String? = null,
    val startedAt: String? = null,
    val completedAt: String? = null,
    val updatedAt: String? = null
)

@JsonClass(generateAdapter = true)
data class JobsMeta(val count: Int, val limit: Int)

@JsonClass(generateAdapter = true)
data class JobsFeed(val data: List<BackendJob>, val meta: JobsMeta, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class JobEnvelope(val data: BackendJob, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class JobEvent(
    val id: String,
    val jobId: String,
    val projectId: String,
    val eventType: String,
    val status: String? = null,
    val progress: Double? = null,
    val payload: Map<String, String> = emptyMap(),
    val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class JobEventsFeed(val data: List<JobEvent>, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class WorkerData(
    val workerId: String,
    val running: Boolean,
    val autostart: Boolean,
    val iterations: Int,
    val lastError: String?
)

@JsonClass(generateAdapter = true)
data class WorkerResponse(val data: WorkerData, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class HealthData(val status: String, val service: String)

@JsonClass(generateAdapter = true)
data class HealthResponse(val status: String, val data: HealthData, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class RecoveryData(val recovered: Int)

@JsonClass(generateAdapter = true)
data class RecoveryResponse(val data: RecoveryData, val requestId: String? = null)
