package com.example.data.api

import com.example.data.*
import retrofit2.http.*

interface FactoryApiService {

    @POST("api/projects")
    suspend fun createProject(@Body request: ProjectCreateRequest): Project

    @POST("api/series")
    suspend fun createSeries(@Body request: SeriesCreateRequest): Series

    @POST("api/episodes")
    suspend fun createEpisode(@Body request: EpisodeCreateRequest): Episode

    @POST("api/scenes")
    suspend fun createScene(@Body request: SceneCreateRequest): Scene

    @POST("api/scenes/{scene_id}/generate")
    suspend fun generateScene(@Path("scene_id") sceneId: String): GenerationJob

    @GET("api/jobs/{job_id}")
    suspend fun getJob(@Path("job_id") jobId: String): GenerationJob
}
