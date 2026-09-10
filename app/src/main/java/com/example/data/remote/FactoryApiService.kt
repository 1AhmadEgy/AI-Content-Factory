package com.example.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

interface FactoryApiService {
    @POST("api/v1/projects")
    suspend fun createProject(@Body request: ProjectCreateRequest): ApiEnvelope<ProjectDto>

    @POST("api/v1/jobs")
    suspend fun createJob(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body request: CreateJobRequest
    ): ApiEnvelope<JobDto>

    @GET("api/v1/jobs/{job_id}")
    suspend fun getJob(@Path("job_id") jobId: String): ApiEnvelope<JobDto>
}
