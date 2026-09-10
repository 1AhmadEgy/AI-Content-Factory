package com.example.data.remote

import com.example.core.model.GenerationJob
import com.example.core.model.Project
import com.example.core.model.ProjectCreateRequest
import com.example.core.model.Episode
import com.example.core.model.EpisodeCreateRequest
import com.example.core.model.Scene
import com.example.core.model.SceneCreateRequest
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface FactoryApiService {
    @POST("api/v1/projects")
    suspend fun createProject(@Body request: ProjectCreateRequest): Project

    @POST("api/v1/episodes")
    suspend fun createEpisode(@Body request: EpisodeCreateRequest): Episode

    @POST("api/v1/scenes")
    suspend fun createScene(@Body request: SceneCreateRequest): Scene

    @POST("api/v1/scenes/{scene_id}/generate")
    suspend fun generateScene(@Path("scene_id") sceneId: String): GenerationJob

    @GET("api/v1/jobs/{job_id}")
    suspend fun getJob(@Path("job_id") jobId: String): GenerationJob
}
