package com.example.feature

import com.example.core.model.*
import com.example.core.theme.*

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Autorenew
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: FactoryViewModel,
    onProjectClick: (String) -> Unit
) {
    val projects by viewModel.projects.collectAsState()
    var showDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AI Content Factory", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue, titleContentColor = PrimaryCyan)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan) {
                Icon(Icons.Filled.Add, "Add Project", tint = DarkBlue)
            }
        },
        containerColor = DarkBlue
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(projects) { project ->
                ProjectCard(project, onClick = { onProjectClick(project.id) })
            }
        }
        
        if (showDialog) {
            AddProjectDialog(
                onDismiss = { showDialog = false },
                onAdd = { name, desc ->
                    viewModel.addProject(name, desc)
                    showDialog = false
                }
            )
        }
    }
}

@Composable
fun ProjectCard(project: Project, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = SurfaceBlue)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(project.name, style = MaterialTheme.typography.titleLarge, color = TextLight)
            Spacer(modifier = Modifier.height(4.dp))
            Text(project.description ?: "No description", style = MaterialTheme.typography.bodyMedium, color = TextMuted)
            Spacer(modifier = Modifier.height(8.dp))
            Badge(containerColor = if (project.status == "ACTIVE") SuccessGreen else WarningOrange) {
                Text(project.status, modifier = Modifier.padding(horizontal = 4.dp))
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectDetailScreen(
    projectId: String,
    viewModel: FactoryViewModel,
    onBack: () -> Unit,
    onSeriesClick: (String) -> Unit,
    onSeriesControlClick: () -> Unit,
) {
    val projects by viewModel.projects.collectAsState()
    val allSeries by viewModel.series.collectAsState()
    val project = projects.find { it.id == projectId }
    val seriesList = allSeries.filter { it.projectId == projectId }

    var showDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(project?.name ?: "Project", color = TextLight) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = TextLight)
                    }
                },
                actions = {
                    TextButton(onClick = onSeriesControlClick) { Text("Series Control", color = PrimaryCyan) }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan) {
                Icon(Icons.Filled.Add, "Add Series", tint = DarkBlue)
            }
        },
        containerColor = DarkBlue
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("Series", style = MaterialTheme.typography.titleMedium, color = PrimaryCyan, modifier = Modifier.padding(bottom = 8.dp))
            }
            items(seriesList) { series ->
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onSeriesClick(series.id) },
                    colors = CardDefaults.cardColors(containerColor = SurfaceBlue)
                ) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Movie, contentDescription = null, tint = SecondaryTeal)
                        Spacer(modifier = Modifier.width(16.dp))
                        Column {
                            Text(series.title, style = MaterialTheme.typography.titleMedium, color = TextLight)
                            Text("Genre: ${series.genre ?: "N/A"}", style = MaterialTheme.typography.bodySmall, color = TextMuted)
                        }
                    }
                }
            }
        }
        
        if (showDialog) {
            AddProjectDialog(
                onDismiss = { showDialog = false },
                onAdd = { name, _ ->
                    viewModel.addSeries(projectId, name)
                    showDialog = false
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SeriesDetailScreen(
    seriesId: String,
    viewModel: FactoryViewModel,
    onBack: () -> Unit,
    onEpisodeClick: (String) -> Unit
) {
    val allSeries by viewModel.series.collectAsState()
    val allEpisodes by viewModel.episodes.collectAsState()
    val series = allSeries.find { it.id == seriesId }
    val episodes = allEpisodes.filter { it.seriesId == seriesId }

    var showDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(series?.title ?: "Series", color = TextLight) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = TextLight)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue)
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan) {
                Icon(Icons.Filled.Add, "Add Episode", tint = DarkBlue)
            }
        },
        containerColor = DarkBlue
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(episodes.sortedBy { it.number }) { ep ->
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onEpisodeClick(ep.id) },
                    colors = CardDefaults.cardColors(containerColor = SurfaceBlue)
                ) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(ep.number.toString(), style = MaterialTheme.typography.headlineSmall, color = PrimaryCyan)
                        Spacer(modifier = Modifier.width(16.dp))
                        Column {
                            Text(ep.title, style = MaterialTheme.typography.titleMedium, color = TextLight)
                            Text("Status: ${ep.status}", style = MaterialTheme.typography.bodySmall, color = TextMuted)
                        }
                    }
                }
            }
        }
        
        if (showDialog) {
            AddProjectDialog(
                onDismiss = { showDialog = false },
                onAdd = { name, _ ->
                    viewModel.addEpisode(seriesId, (episodes.maxOfOrNull { it.number } ?: 0) + 1, name)
                    showDialog = false
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EpisodeDetailScreen(
    episodeId: String,
    viewModel: FactoryViewModel,
    onBack: () -> Unit
) {
    val allEpisodes by viewModel.episodes.collectAsState()
    val allScenes by viewModel.scenes.collectAsState()
    val allJobs by viewModel.jobs.collectAsState()
    
    val episode = allEpisodes.find { it.id == episodeId }
    val scenes = allScenes.filter { it.episodeId == episodeId }.sortedBy { it.number }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(episode?.title ?: "Episode", color = TextLight) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = TextLight)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue)
            )
        },
        containerColor = DarkBlue
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("Scenes", style = MaterialTheme.typography.titleMedium, color = PrimaryCyan)
            }
            items(scenes) { scene ->
                val job = allJobs.find { it.targetId == scene.id }
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Scene ${scene.number}", style = MaterialTheme.typography.titleMedium, color = TextLight)
                            Spacer(Modifier.weight(1f))
                            Text(scene.status, color = when (scene.status) {
                                "DONE" -> SuccessGreen
                                "FAILED" -> ErrorRed
                                else -> WarningOrange
                            })
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(scene.description, color = TextMuted)
                        Text("Location: ${scene.location}", color = TextMuted)
                        Text("Emotion: ${scene.emotion}", color = TextMuted)
                        job?.let { Text("Job: ${it.status} · ${it.progress}%", color = PrimaryCyan) }
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = { viewModel.generateScene(scene.id) }) {
                            Icon(Icons.Filled.PlayArrow, contentDescription = null)
                            Spacer(Modifier.width(6.dp))
                            Text("Generate")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AddProjectDialog(onDismiss: () -> Unit, onAdd: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") })
                OutlinedTextField(value = description, onValueChange = { description = it }, label = { Text("Description") })
            }
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onAdd(name.trim(), description.trim()) }) { Text("Create") }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancel") } }
    )
}
