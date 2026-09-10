package com.example.data.repository

import android.util.Log
import com.example.core.model.*
import com.example.data.local.FactoryDao
import com.example.data.remote.BackendJob
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
    private val isoParser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSX", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }

    val projects: StateFlow<List<Project>> = dao.getAllProjects().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val series: StateFlow<List<Series>> = dao.getAllSeries().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val episodes: StateFlow<List<Episode>> = dao.getAllEpisodes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val scenes: StateFlow<List<Scene>> = dao.getAllScenes().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())
    val jobs: StateFlow<List<GenerationJob>> = dao.getAllJobs().stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        scope.launch {
            if (dao.getAllProjects().firstOrNull()?.isEmpty() == true) {
                val defaultProject = Project(name = "My AI Series", description = "Arabic comedy series")
                dao.insertProject(defaultProject)
                val defaultSeries = Series(projectId = defaultProject.id, title = "Pilot Series", genre = "Comedy")
                dao.insertSeries(defaultSeries)
                val ep1 = Episode(seriesId = defaultSeries.id, number = 1, title = "The Beginning")
                dao.insertEpisode(ep1)
                dao.insertScene(Scene(episodeId = ep1.id, number = 1, description = "A character enters the room surprised", location = "Living Room", emotion = "Surprise"))
                dao.insertScene(Scene(episodeId = ep1.id, number = 2, description = "Character finds a mysterious box", location = "Living Room", emotion = "Curiosity"))
            }
            syncJobs()
        }
    }

    suspend fun addProject(name: String, description: String) {
        try { dao.insertProject(api.createProject(ProjectCreateRequest(name, description))) }
        catch (e: Exception) { Log.e("Repository", "createProject failed", e); dao.insertProject(Project(name = name, description = description)) }
    }

    suspend fun addSeries(projectId: String, title: String) {
        try { dao.insertSeries(api.createSeries(SeriesCreateRequest(projectId = projectId, title = title))) }
        catch (e: Exception) { Log.e("Repository", "createSeries failed", e); dao.insertSeries(Series(projectId = projectId, title = title)) }
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        try { dao.insertEpisode(api.createEpisode(EpisodeCreateRequest(seriesId = seriesId, number = number, title = title))) }
        catch (e: Exception) { Log.e("Repository", "createEpisode failed", e); dao.insertEpisode(Episode(seriesId = seriesId, number = number, title = title)) }
    }

    suspend fun generateScene(sceneId: String) {
        val scene = scenes.value.find { it.id == sceneId } ?: return
        scene.status = "QUEUED"
        dao.updateScene(scene)
        try {
            val response = api.generateScene(sceneId)
            dao.insertJob(response)
        } catch (e: Exception) {
            Log.e("Repository", "generateScene failed", e)
            scene.status = "FAILED"
            dao.updateScene(scene)
            return
        }
        syncJobs()
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
        status = runCatching { JobStatus.valueOf(status.uppercase()) }.getOrDefault(JobStatus.FAILED),
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
        completedAt = parseTime(completedAt)
    )

    suspend fun syncJobs(projectId: String? = null) {
        try {
            val feed = api.listJobs(projectId = projectId, limit = 200)
            feed.data.forEach { dao.insertJob(it.toLocalJob()) }
        } catch (e: Exception) { Log.w("Repository", "Job sync unavailable; retaining local state", e) }
    }

    suspend fun cancelJob(jobId: String): GenerationJob? = try {
        api.cancelJob(jobId).data.toLocalJob().also { dao.insertJob(it) }
    } catch (e: Exception) { Log.e("Repository", "cancelJob failed", e); null }

    suspend fun retryJob(jobId: String): GenerationJob? = try {
        api.retryJob(jobId).data.toLocalJob().also { dao.insertJob(it) }
    } catch (e: Exception) { Log.e("Repository", "retryJob failed", e); null }

    suspend fun refreshJob(jobId: String) {
        try { api.getJob(jobId).data.toLocalJob().also { dao.insertJob(it) } }
        catch (e: Exception) { Log.w("Repository", "refreshJob failed", e) }
    }
}

object Graph {
    lateinit var repository: Repository
    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
