package com.example.data.remote

import com.example.core.model.EpisodeCreateRequest
import com.example.core.model.ProjectCreateRequest
import com.example.core.model.SeriesCreateRequest
import com.example.core.model.SceneCreateRequest
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface FactoryApiService {
    @POST("api/v1/projects")
    suspend fun createProject(@Body request: ProjectCreateRequest): ProjectEnvelope

    @GET("api/v1/jobs/{job_id}")
    suspend fun getJob(@Path("job_id") jobId: String): JobEnvelope

    @GET("api/v1/jobs")
    suspend fun listJobs(
        @Query("projectId") projectId: String? = null,
        @Query("status") status: String? = null,
        @Query("limit") limit: Int = 50,
    ): JobsFeed

    @POST("api/v1/jobs")
    suspend fun createJob(
        @Body request: CreateJobRequest,
        @Header("Idempotency-Key") idempotencyKey: String,
    ): JobEnvelope

    @POST("api/v1/jobs/{job_id}/cancel")
    suspend fun cancelJob(@Path("job_id") jobId: String): JobEnvelope

    @POST("api/v1/jobs/{job_id}/pause")
    suspend fun pauseJob(@Path("job_id") jobId: String): JobEnvelope

    @POST("api/v1/jobs/{job_id}/resume")
    suspend fun resumeJob(@Path("job_id") jobId: String): JobEnvelope

    @POST("api/v1/jobs/{job_id}/retry")
    suspend fun retryJob(@Path("job_id") jobId: String): JobEnvelope

    @GET("api/v1/jobs/{job_id}/events")
    suspend fun getJobEvents(
        @Path("job_id") jobId: String,
        @Query("limit") limit: Int = 200,
    ): JobEventsFeed

    @GET("api/v1/jobs/{job_id}/provider-runs")
    suspend fun getProviderRuns(
        @Path("job_id") jobId: String,
        @Query("limit") limit: Int = 50,
    ): ProviderRunsFeed

    @GET("api/v1/health")
    suspend fun health(): HealthResponse

    @GET("api/v1/worker/status")
    suspend fun workerStatus(): WorkerResponse
}
