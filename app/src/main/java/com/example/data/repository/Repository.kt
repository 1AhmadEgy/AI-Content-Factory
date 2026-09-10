package com.example.data.repository

import com.example.core.model.*
import com.example.data.remote.NetworkClient
import com.example.data.local.FactoryDao
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
        scope.launch {
            if (dao.getAllProjects().firstOrNull()?.isEmpty() == true) {
                Log.i("Repository", "Local database is empty; waiting for backend data")
            }
        }
    }

    suspend fun addProject(name: String, description: String) {
        val response = api.createProject(ProjectCreateRequest(name, description))
        dao.insertProject(response)
    }

    suspend fun addEpisode(seriesId: String, number: Int, title: String) {
        val response = api.createEpisode(EpisodeCreateRequest(seriesId = seriesId, number = number, title = title))
        dao.insertEpisode(response)
    }

    suspend fun generateScene(sceneId: String) {
        val response = api.generateScene(sceneId)
        dao.insertJob(response)
        refreshJob(response.id)
    }

    suspend fun refreshJob(jobId: String) {
        val response = api.getJob(jobId)
        dao.updateJob(response)
    }
}

object Graph {
    lateinit var repository: Repository

    fun provide(context: android.content.Context) {
        val database = com.example.data.local.FactoryDatabase.getDatabase(context)
        repository = Repository(database.factoryDao())
    }
}
