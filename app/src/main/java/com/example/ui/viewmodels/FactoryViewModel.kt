package com.example.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import com.example.data.Graph
import com.example.data.Project
import com.example.data.Series
import com.example.data.Episode
import com.example.data.Scene
import com.example.data.GenerationJob
import kotlinx.coroutines.flow.StateFlow

class FactoryViewModel : ViewModel() {
    private val repo = Graph.repository

    val projects: StateFlow<List<Project>> = repo.projects
    val series: StateFlow<List<Series>> = repo.series
    val episodes: StateFlow<List<Episode>> = repo.episodes
    val scenes: StateFlow<List<Scene>> = repo.scenes
    val jobs: StateFlow<List<GenerationJob>> = repo.jobs

    fun addProject(name: String, description: String) {
        viewModelScope.launch {
            repo.addProject(name, description)
        }
    }

    fun addSeries(projectId: String, title: String) {
        viewModelScope.launch {
            repo.addSeries(projectId, title)
        }
    }

    fun addEpisode(seriesId: String, number: Int, title: String) {
        viewModelScope.launch {
            repo.addEpisode(seriesId, number, title)
        }
    }

    fun generateScene(sceneId: String) {
        viewModelScope.launch {
            repo.generateScene(sceneId)
        }
    }
}
