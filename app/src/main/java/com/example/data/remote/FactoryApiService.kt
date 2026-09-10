package com.example.data.remote

import com.example.core.model.*
import retrofit2.http.*

interface FactoryApiService {
    @POST("api/v1/projects") suspend fun createProject(@Body request: ProjectCreateRequest): Project
    @POST("api/v1/series") suspend fun createSeries(@Body request: SeriesCreateRequest): Series
    @POST("api/v1/episodes") suspend fun createEpisode(@Body request: EpisodeCreateRequest): Episode
    @POST("api/v1/scenes") suspend fun createScene(@Body request: SceneCreateRequest): Scene
    @POST("api/v1/scenes/{scene_id}/generate") suspend fun generateScene(@Path("scene_id") sceneId: String): GenerationJob
    @GET("api/v1/jobs/{job_id}") suspend fun getJob(@Path("job_id") jobId: String): Map<String, Any?>
    @GET("api/v1/jobs") suspend fun listJobs(@Query("projectId") projectId: String? = null,@Query("status") status: String? = null,@Query("limit") limit: Int = 50): JobsFeed
    @POST("api/v1/jobs/{job_id}/cancel") suspend fun cancelJob(@Path("job_id") jobId: String): Map<String, Any?>
    @POST("api/v1/jobs/{job_id}/pause") suspend fun pauseJob(@Path("job_id") jobId: String): Map<String, Any?>
    @POST("api/v1/jobs/{job_id}/resume") suspend fun resumeJob(@Path("job_id") jobId: String): Map<String, Any?>
    @POST("api/v1/jobs/{job_id}/retry") suspend fun retryJob(@Path("job_id") jobId: String): Map<String, Any?>
    @GET("api/v1/jobs/{job_id}/events") suspend fun getJobEvents(@Path("job_id") jobId: String,@Query("limit") limit: Int = 200): JobEventsFeed
    @POST("api/v1/batches/{batch_id}/cancel") suspend fun cancelBatch(@Path("batch_id") batchId: String): Map<String, Any?>
    @POST("api/v1/batches/{batch_id}/retry") suspend fun retryBatch(@Path("batch_id") batchId: String): Map<String, Any?>
    @GET("api/v1/batches/{batch_id}") suspend fun getBatch(@Path("batch_id") batchId: String): Map<String, Any?>
    @GET("api/v1/schedules/{schedule_id}") suspend fun getSchedule(@Path("schedule_id") scheduleId: String): Map<String, Any?>
    @POST("api/v1/schedules/{schedule_id}/pause") suspend fun pauseSchedule(@Path("schedule_id") scheduleId: String): Map<String, Any?>
    @POST("api/v1/schedules/{schedule_id}/resume") suspend fun resumeSchedule(@Path("schedule_id") scheduleId: String): Map<String, Any?>
    @DELETE("api/v1/schedules/{schedule_id}") suspend fun deleteSchedule(@Path("schedule_id") scheduleId: String)
    @GET("api/v1/health") suspend fun health(): HealthResponse
    @GET("api/v1/worker/status") suspend fun workerStatus(): WorkerResponse
    @GET("api/v1/scheduler/status") suspend fun schedulerStatus(): SchedulerResponse
}
