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
import kotlinx.coroutines.flow.firstOrNull
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
        scope.launch {
            if (dao.getAllProjects().firstOrNull()?.isEmpty() == true) {
                val project = Project(name = "My AI Series", description = "Arabic comedy series")
                dao.insertProject(project)
                val series = Series(projectId = project.id, title = "Pilot Series", genre = "Comedy")
                dao.insertSeries(series)
                val episode = Episode(seriesId = series.id, number = 1, title = "The Beginning")
                dao.insertEpisode(episode)
                dao.insertScene(Scene(episodeId = episode.id, number = 1, description = "A character enters the room surprised", location = "Living Room", emotion = "Surprise"))
                dao.insertScene(Scene(episodeId = episode.id, number = 2, description = "Character finds a mysterious box", location = "Living Room", emotion = "Curiosity"))
            }
            syncJobs()
        }
    }

    suspend fun addProject(name: String, description: String) {
        try {
            val project = api.createProject(ProjectCreateRequest(name, description)).data
            dao.insertProject(Project(id = project.id, name = project.name, description = project.description))
        } catch (e: Exception) {
            Log.e("Repository", "createProject failed", e)
        }
    }

    suspend fun addSeries(projectId: String, title: String) {
        // Series are currently local-first; the backend has no series endpoint.
        dao.insertSeries(Series(projectId = projectId, title = title))
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        // Episodes are currently local-first; the backend has no episode endpoint.
        dao.insertEpisode(Episode(seriesId = seriesId, number = number, title = title))
    }

    suspend fun generateScene(sceneId: String) {
        val scene = scenes.value.find { it.id == sceneId } ?: return
        val projectId = dao.findProjectIdForScene(sceneId)
        if (projectId == null) {
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
                    provider = "mock",
                    model = "mock-deterministic",
                    input = JobInputRequest(
                        parameters = mapOf("sceneId" to sceneId, "description" to scene.description, "location" to scene.location, "emotion" to scene.emotion),
                        deterministic = true,
                    ),
                ),
                idempotencyKey = "android-scene-$sceneId",
            )
            dao.insertJob(response.data.toLocalJob())
        } catch (e: Exception) {
            Log.e("Repository", "generateScene failed", e)
            scene.status = "FAILED"
            dao.updateScene(scene)
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
        try {
            api.listJobs(projectId = projectId, limit = 200).data.forEach { dao.insertJob(it.toLocalJob()) }
        } catch (e: Exception) {
            Log.w("Repository", "Job sync unavailable; retaining local state", e)
        }
    }

    suspend fun cancelJob(jobId: String): GenerationJob? = runCatching {
        api.cancelJob(jobId).data.toLocalJob().also { dao.insertJob(it) }
    }.onFailure { Log.e("Repository", "cancelJob failed", it) }.getOrNull()

    suspend fun retryJob(jobId: String): GenerationJob? = runCatching {
        api.retryJob(jobId).data.toLocalJob().also { dao.insertJob(it) }
    }.onFailure { Log.e("Repository", "retryJob failed", it) }.getOrNull()

    suspend fun refreshJob(jobId: String) {
        runCatching { api.getJob(jobId).data.toLocalJob().also { dao.insertJob(it) } }
            .onFailure { Log.w("Repository", "refreshJob failed", it) }
    }
}

object Graph {
    lateinit var repository: Repository

    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
