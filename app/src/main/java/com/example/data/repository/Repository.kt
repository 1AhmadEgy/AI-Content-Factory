package com.example.data.repository

import android.util.Log
import com.example.core.model.*
import com.example.data.local.FactoryDao
import com.example.data.remote.BackendJob
import com.example.data.remote.CreateJobRequest
import com.example.data.remote.JobInputRequest
import com.example.data.remote.NetworkClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class Repository(private val dao: FactoryDao) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private val api = NetworkClient.apiService
    private val isoParser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSX", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    val projects: StateFlow<List<Project>> = dao.getAllProjects().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val series: StateFlow<List<Series>> = dao.getAllSeries().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val episodes: StateFlow<List<Episode>> = dao.getAllEpisodes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val scenes: StateFlow<List<Scene>> = dao.getAllScenes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val jobs: StateFlow<List<GenerationJob>> = dao.getAllJobs().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        scope.launch { syncJobs() }
    }

    suspend fun addProject(name: String, description: String) {
        try {
            val project = api.createProject(ProjectCreateRequest(name, description)).data
            dao.insertProject(Project(id = project.id, name = project.name, description = project.description))
        } catch (e: Exception) {
            Log.e("Repository", "createProject failed", e)
            throw e
        }
    }

    suspend fun addSeries(projectId: String, title: String) {
        dao.insertSeries(Series(projectId = projectId, title = title))
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        val episode = Episode(seriesId = seriesId, number = number, title = title)
        dao.insertEpisode(episode)
        dao.findProjectIdForSeries(seriesId)?.let { projectId -> snapshotEpisodeContext(projectId, episode.id) }
    }

    private suspend fun snapshotEpisodeContext(projectId: String, episodeId: String) {
        api.snapshotEpisodeContext(projectId, episodeId)
    }

    suspend fun generateScene(sceneId: String) {
        val scene = scenes.value.find { it.id == sceneId } ?: return
        val projectId = dao.findProjectIdForScene(sceneId) ?: run {
            scene.status = "FAILED"
            dao.updateScene(scene)
            return
        }
        scene.status = "QUEUED"
        dao.updateScene(scene)
        try {
            val response = api.createJob(
                request = CreateJobRequest(
                    projectId = projectId,
                    type = "IMAGE",
                    targetType = "scene",
                    targetId = sceneId,
                    provider = "openai",
                    model = "gpt-image-2",
                    input = JobInputRequest(
                        parameters = mapOf(
                            "prompt" to "${scene.description}. Location: ${scene.location}. Emotion: ${scene.emotion}. Create a production-ready cinematic frame with consistent character and environment identity.",
                            "sceneId" to sceneId,
                            "description" to scene.description,
                            "location" to scene.location,
                            "emotion" to scene.emotion,
                        ),
                        deterministic = false,
                    ),
                ),
                idempotencyKey = "android-scene-$sceneId",
            )
            dao.insertJob(response.data.toLocalJob())
        } catch (e: Exception) {
            Log.e("Repository", "generateScene failed", e)
            scene.status = "FAILED"
            dao.updateScene(scene)
            throw e
        }
    }

    private fun parseTime(value: String?): Long? {
        if (value == null) return null
        val normalized = value.replace(Regex("\\.(\\d{3})\\d*Z$"), ".$1Z")
        return runCatching { synchronized(isoParser) { isoParser.parse(normalized)?.time } }.getOrNull()
    }

    private fun BackendJob.toLocalJob(): GenerationJob = GenerationJob(
        id = id,
        jobType = type,
        targetType = targetType,
        targetId = targetId,
        status = runCatching { JobStatus.valueOf(status.uppercase(Locale.US)) }.getOrDefault(JobStatus.FAILED),
        priority = priority,
        attempt = attempt,
        maxAttempts = maxAttempts,
        provider = provider,
        model = model,
        progress = (progress.coerceIn(0.0, 1.0) * 100).toInt(),
        errorCode = errorCode,
        errorMessage = errorMessage,
        createdAt = parseTime(createdAt) ?: System.currentTimeMillis(),
        startedAt = parseTime(startedAt),
        completedAt = parseTime(completedAt),
    )

    suspend fun syncJobs(projectId: String? = null) {
        api.listJobs(projectId = projectId, limit = 200).data.forEach { dao.insertJob(it.toLocalJob()) }
    }

    suspend fun cancelJob(jobId: String): GenerationJob? = api.cancelJob(jobId).data.toLocalJob().also { dao.insertJob(it) }

    suspend fun retryJob(jobId: String): GenerationJob? = api.retryJob(jobId).data.toLocalJob().also { dao.insertJob(it) }

    suspend fun refreshJob(jobId: String) {
        dao.insertJob(api.getJob(jobId).data.toLocalJob())
    }
}

object Graph {
    lateinit var repository: Repository

    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
