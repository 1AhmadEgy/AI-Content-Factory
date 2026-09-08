package com.example.data

import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class Repository {
    private val scope = CoroutineScope(Dispatchers.Default)

    private val _projects = MutableStateFlow<List<Project>>(emptyList())
    val projects: StateFlow<List<Project>> = _projects.asStateFlow()

    private val _series = MutableStateFlow<List<Series>>(emptyList())
    val series: StateFlow<List<Series>> = _series.asStateFlow()

    private val _episodes = MutableStateFlow<List<Episode>>(emptyList())
    val episodes: StateFlow<List<Episode>> = _episodes.asStateFlow()

    private val _scenes = MutableStateFlow<List<Scene>>(emptyList())
    val scenes: StateFlow<List<Scene>> = _scenes.asStateFlow()

    private val _jobs = MutableStateFlow<List<GenerationJob>>(emptyList())
    val jobs: StateFlow<List<GenerationJob>> = _jobs.asStateFlow()

    init {
        // Pre-populate some mock data
        val defaultProject = Project(name = "My AI Series", description = "Arabic comedy series")
        _projects.update { it + defaultProject }

        val defaultSeries = Series(projectId = defaultProject.id, title = "Pilot Series", genre = "Comedy")
        _series.update { it + defaultSeries }

        val ep1 = Episode(seriesId = defaultSeries.id, number = 1, title = "The Beginning")
        _episodes.update { it + ep1 }

        val s1 = Scene(episodeId = ep1.id, number = 1, description = "A character enters the room surprised", location = "Living Room", emotion = "Surprise")
        val s2 = Scene(episodeId = ep1.id, number = 2, description = "Character finds a mysterious box", location = "Living Room", emotion = "Curiosity")
        _scenes.update { it + s1 + s2 }
    }

    fun addProject(name: String, description: String) {
        val p = Project(name = name, description = description)
        _projects.update { it + p }
    }

    fun addSeries(projectId: String, title: String) {
        val s = Series(projectId = projectId, title = title)
        _series.update { it + s }
    }

    fun addEpisode(seriesId: String, number: Int, title: String) {
        val e = Episode(seriesId = seriesId, number = number, title = title)
        _episodes.update { it + e }
    }

    fun generateScene(sceneId: String) {
        val scene = _scenes.value.find { it.id == sceneId } ?: return
        
        // Update scene status
        _scenes.update { scenes ->
            scenes.map { if (it.id == sceneId) it.copy(status = "VIDEO_PENDING") else it }
        }

        val job = GenerationJob(
            jobType = "SCENE_GENERATION",
            targetType = "SCENE",
            targetId = sceneId,
            provider = "mock"
        )
        _jobs.update { it + job }

        // Mock job execution
        scope.launch {
            _jobs.update { jobs ->
                jobs.map { if (it.id == job.id) it.copy(status = JobStatus.RUNNING, progress = 5) else it }
            }
            for (progress in listOf(20, 40, 60, 80, 100)) {
                delay(800) // Simulate processing time
                _jobs.update { jobs ->
                    jobs.map { if (it.id == job.id) it.copy(progress = progress) else it }
                }
            }
            _jobs.update { jobs ->
                jobs.map { if (it.id == job.id) it.copy(status = JobStatus.COMPLETED) else it }
            }
            _scenes.update { scenes ->
                scenes.map { if (it.id == sceneId) it.copy(status = "APPROVED") else it }
            }
        }
    }
}

// Singleton for simplicity in MVP
object Graph {
    val repository = Repository()
}
