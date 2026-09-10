package com.example.feature

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.model.*
import com.example.data.repository.Graph
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class FactoryViewModel : ViewModel() {
    private val repo = Graph.repository
    val projects: StateFlow<List<Project>> = repo.projects
    val series: StateFlow<List<Series>> = repo.series
    val episodes: StateFlow<List<Episode>> = repo.episodes
    val scenes: StateFlow<List<Scene>> = repo.scenes
    val jobs: StateFlow<List<GenerationJob>> = repo.jobs

    fun addProject(name: String, description: String) = viewModelScope.launch { repo.addProject(name, description) }
    fun addSeries(projectId: String, title: String) = viewModelScope.launch { repo.addSeries(projectId, title) }
    fun addEpisode(seriesId: String, number: Int, title: String) = viewModelScope.launch { repo.addEpisode(seriesId, number, title) }
    fun generateScene(sceneId: String) = viewModelScope.launch { repo.generateScene(sceneId) }
    fun refreshJobs(projectId: String? = null) = viewModelScope.launch { repo.syncJobs(projectId) }
    fun refreshJob(jobId: String) = viewModelScope.launch { repo.refreshJob(jobId) }
    fun cancelJob(jobId: String) = viewModelScope.launch { repo.cancelJob(jobId) }
}
