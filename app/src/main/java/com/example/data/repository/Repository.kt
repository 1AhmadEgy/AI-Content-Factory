package com.example.data.repository

import com.example.core.model.*

import com.example.data.remote.NetworkClient
import com.example.data.local.FactoryDao
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import android.util.Log
import kotlinx.coroutines.flow.firstOrNull

class Repository(private val dao: FactoryDao) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private val api = NetworkClient.apiService

    val projects: StateFlow<List<Project>> = dao.getAllProjects()
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    val series: StateFlow<List<Series>> = dao.getAllSeries()
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    val episodes: StateFlow<List<Episode>> = dao.getAllEpisodes()
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    val scenes: StateFlow<List<Scene>> = dao.getAllScenes()
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    val jobs: StateFlow<List<GenerationJob>> = dao.getAllJobs()
        .stateIn(scope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        // Pre-populate mock data only if DB is empty
        scope.launch {
            if (dao.getAllProjects().firstOrNull()?.isEmpty() == true) {
                val defaultProject = Project(name = "My AI Series", description = "Arabic comedy series")
                dao.insertProject(defaultProject)

                val defaultSeries = Series(projectId = defaultProject.id, title = "Pilot Series", genre = "Comedy")
                dao.insertSeries(defaultSeries)

                val ep1 = Episode(seriesId = defaultSeries.id, number = 1, title = "The Beginning")
                dao.insertEpisode(ep1)

                val s1 = Scene(episodeId = ep1.id, number = 1, description = "A character enters the room surprised", location = "Living Room", emotion = "Surprise")
                val s2 = Scene(episodeId = ep1.id, number = 2, description = "Character finds a mysterious box", location = "Living Room", emotion = "Curiosity")
                dao.insertScene(s1)
                dao.insertScene(s2)
            }
        }
    }

    suspend fun addProject(name: String, description: String) {
        try {
            val response = api.createProject(ProjectCreateRequest(name, description))
            dao.insertProject(response)
        } catch (e: Exception) {
            Log.e("Repository", "Network failed, using local fallback", e)
            val p = Project(name = name, description = description)
            dao.insertProject(p)
        }
    }

    suspend fun addSeries(projectId: String, title: String) {
        try {
            val response = api.createSeries(SeriesCreateRequest(projectId = projectId, title = title))
            dao.insertSeries(response)
        } catch (e: Exception) {
            Log.e("Repository", "Network failed, using local fallback", e)
            val s = Series(projectId = projectId, title = title)
            dao.insertSeries(s)
        }
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        try {
            val response = api.createEpisode(EpisodeCreateRequest(seriesId = seriesId, number = number, title = title))
            dao.insertEpisode(response)
        } catch (e: Exception) {
            Log.e("Repository", "Network failed, using local fallback", e)
            val eLocal = Episode(seriesId = seriesId, number = number, title = title)
            dao.insertEpisode(eLocal)
        }
    }

    suspend fun generateScene(sceneId: String) {
        val scene = scenes.value.find { it.id == sceneId } ?: return
        
        scene.status = "VIDEO_PENDING"
        dao.updateScene(scene)

        try {
            val response = api.generateScene(sceneId)
            dao.insertJob(response)
            simulateJobProgress(response, scene)
        } catch (e: Exception) {
            Log.e("Repository", "Network failed, using local fallback", e)
            val job = GenerationJob(
                jobType = "SCENE_GENERATION",
                targetType = "SCENE",
                targetId = sceneId,
                provider = "mock"
            )
            dao.insertJob(job)
            simulateJobProgress(job, scene)
        }
    }

    private fun simulateJobProgress(job: GenerationJob, scene: Scene) {
        scope.launch {
            job.status = JobStatus.RUNNING
            job.progress = 5
            dao.updateJob(job)
            
            for (progress in listOf(20, 40, 60, 80, 100)) {
                delay(800)
                job.progress = progress
                dao.updateJob(job)
            }
            
            job.status = JobStatus.COMPLETED
            dao.updateJob(job)
            
            scene.status = "APPROVED"
            dao.updateScene(scene)
        }
    }
}

// Singleton for simplicity in MVP
object Graph {
    lateinit var repository: Repository
    
    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
