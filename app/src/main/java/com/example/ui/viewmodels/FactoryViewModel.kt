package com.example.ui.viewmodels

import androidx.lifecycle.ViewModel
import com.example.data.Graph
import com.example.data.Project
import com.example.data.Series
import com.example.data.Episode
import com.example.data.Scene
import com.example.data.GenerationJob
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map

class FactoryViewModel : ViewModel() {
    private val repo = Graph.repository

    val projects: StateFlow<List<Project>> = repo.projects
    val series: StateFlow<List<Series>> = repo.series
    val episodes: StateFlow<List<Episode>> = repo.episodes
    val scenes: StateFlow<List<Scene>> = repo.scenes
    val jobs: StateFlow<List<GenerationJob>> = repo.jobs

    fun addProject(name: String, description: String) {
        repo.addProject(name, description)
    }

    fun addSeries(projectId: String, title: String) {
        repo.addSeries(projectId, title)
    }

    fun addEpisode(seriesId: String, number: Int, title: String) {
        repo.addEpisode(seriesId, number, title)
    }

    fun generateScene(sceneId: String) {
        repo.generateScene(sceneId)
    }
}
