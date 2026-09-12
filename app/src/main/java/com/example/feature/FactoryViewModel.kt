package com.example.feature

import android.util.Log
import com.example.core.model.*
import com.example.data.repository.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun clearError() {
        _error.value = null
    }

    private fun reportError(operation: String, throwable: Throwable) {
        Log.e("FactoryViewModel", operation, throwable)
        _error.value = throwable.message ?: "$operation failed"
    }

    fun addProject(name: String, description: String) {
        viewModelScope.launch {
            runCatching { repo.addProject(name, description) }
                .onFailure { reportError("Create project", it) }
        }
    }

    fun addSeries(projectId: String, title: String) {
        viewModelScope.launch {
            runCatching { repo.addSeries(projectId, title) }
                .onFailure { reportError("Create series", it) }
        }
    }

    fun addEpisode(seriesId: String, number: Int, title: String) {
        viewModelScope.launch {
            runCatching { repo.addEpisode(seriesId, number, title) }
                .onFailure { reportError("Create episode", it) }
        }
    }

    fun generateScene(sceneId: String) {
        viewModelScope.launch {
            runCatching { repo.generateScene(sceneId) }
                .onFailure { reportError("Generate scene", it) }
        }
    }
}
