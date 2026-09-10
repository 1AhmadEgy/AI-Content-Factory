package com.example.data.repository

import com.example.core.model.*
import com.example.data.remote.*
import com.example.data.local.FactoryDao
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class Repository(private val dao: FactoryDao) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private val api = NetworkClient.apiService
    val projects: StateFlow<List<Project>> = dao.getAllProjects().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val series: StateFlow<List<Series>> = dao.getAllSeries().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val episodes: StateFlow<List<Episode>> = dao.getAllEpisodes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val scenes: StateFlow<List<Scene>> = dao.getAllScenes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val jobs: StateFlow<List<GenerationJob>> = dao.getAllJobs().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    suspend fun addProject(name: String, description: String) {
        dao.insertProject(api.createProject(ProjectCreateRequest(name)).data.toDomain())
    }

    suspend fun addSeries(projectId: String, title: String) {
        dao.insertSeries(Series(projectId = projectId, title = title))
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        dao.insertEpisode(Episode(seriesId = seriesId, number = number, title = title))
    }

    suspend fun generateScene(sceneId: String) {
        val scene = dao.getScene(sceneId) ?: throw IllegalArgumentException("SCENE_NOT_FOUND")
        val episode = dao.getEpisode(scene.episodeId) ?: throw IllegalArgumentException("EPISODE_NOT_FOUND")
        val series = dao.getSeries(episode.seriesId) ?: throw IllegalArgumentException("SERIES_NOT_FOUND")
        val response = api.createJob(
            idempotencyKey = "android-scene-$sceneId",
            request = CreateJobRequest(
                projectId = series.projectId,
                type = "VIDEO",
                targetType = "SCENE",
                targetId = sceneId,
                provider = "mock",
                input = JobInputDto(parameters = mapOf("sceneId" to sceneId, "description" to scene.description), deterministic = true),
            ),
        )
        dao.insertJob(response.data.toDomain())
        refreshJob(response.data.id)
    }

    suspend fun refreshJob(jobId: String) {
        dao.updateJob(api.getJob(jobId).data.toDomain())
    }
}

private fun ProjectDto.toDomain() = Project(id = id, name = name)

private fun JobDto.toDomain() = GenerationJob(
    id = id,
    jobType = type,
    targetType = targetType,
    targetId = targetId ?: "",
    status = runCatching { JobStatus.valueOf(status) }.getOrDefault(JobStatus.FAILED),
    priority = priority,
    attempt = attempt,
    maxAttempts = maxAttempts,
    provider = provider,
    model = model,
    input = input?.toString(),
    output = output?.toString(),
    progress = (progress.coerceIn(0.0, 1.0) * 100).toInt(),
    error = errorCode ?: errorMessage,
)

object Graph {
    lateinit var repository: Repository
    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
