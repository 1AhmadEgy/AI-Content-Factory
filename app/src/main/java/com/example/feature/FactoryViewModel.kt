package com.example.feature

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.model.*
import com.example.data.repository.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class FactoryViewModel : ViewModel() {
    private val repo = Graph.repository

    val projects: StateFlow<List<Project>> = repo.projects
    val series: StateFlow<List<Series>> = repo.series
    val episodes: StateFlow<List<Episode>> = repo.episodes
    val scenes: StateFlow<List<Scene>> = repo.scenes
    val jobs: StateFlow<List<GenerationJob>> = repo.jobs

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun clearError() {
        _errorMessage.value = null
    }

    private fun launchSafely(block: suspend () -> Unit) {
        viewModelScope.launch {
            try {
                block()
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                _errorMessage.value = error.message?.takeIf { it.isNotBlank() } ?: "Unexpected error"
            }
        }
    }

    fun addProject(name: String, description: String) = launchSafely {
        repo.addProject(name, description)
    }

    fun addSeries(projectId: String, title: String) = launchSafely {
        repo.addSeries(projectId, title)
    }

    fun addEpisode(seriesId: String, number: Int, title: String) = launchSafely {
        repo.addEpisode(seriesId, number, title)
    }

    fun generateScene(sceneId: String) = launchSafely {
        repo.generateScene(sceneId)
    }
}
