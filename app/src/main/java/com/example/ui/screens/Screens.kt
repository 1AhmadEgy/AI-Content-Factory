package com.example.ui.screens

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
import com.example.data.*
import com.example.ui.viewmodels.FactoryViewModel
import com.example.ui.theme.*

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
    onSeriesClick: (String) -> Unit
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
            AddProjectDialog( // Reusing simplified dialog
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
                Text("Scenes (Production Plan)", style = MaterialTheme.typography.titleMedium, color = PrimaryCyan)
                Spacer(modifier = Modifier.height(8.dp))
            }
            items(scenes) { scene ->
                val sceneJobs = allJobs.filter { it.targetId == scene.id }
                val latestJob = sceneJobs.maxByOrNull { it.id } // Simplification

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = SurfaceBlue)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Badge(containerColor = SecondaryTeal) { Text("Scene ${scene.number}") }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(scene.location ?: "Unknown Location", style = MaterialTheme.typography.labelLarge, color = TextMuted)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(scene.description, style = MaterialTheme.typography.bodyLarge, color = TextLight)
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                            Text("Status: ${scene.status}", color = when(scene.status) {
                                "APPROVED" -> SuccessGreen
                                "VIDEO_PENDING" -> WarningOrange
                                else -> TextMuted
                            })
                            
                            Button(
                                onClick = { viewModel.generateScene(scene.id) },
                                colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan),
                                enabled = scene.status != "VIDEO_PENDING"
                            ) {
                                Icon(Icons.Filled.PlayArrow, contentDescription = "Generate", tint = DarkBlue)
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Generate", color = DarkBlue)
                            }
                        }
                        
                        if (latestJob != null && latestJob.status == JobStatus.RUNNING) {
                            Spacer(modifier = Modifier.height(8.dp))
                            LinearProgressIndicator(
                                progress = { latestJob.progress / 100f },
                                modifier = Modifier.fillMaxWidth(),
                                color = PrimaryCyan
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun QueueScreen(viewModel: FactoryViewModel) {
    val jobs by viewModel.jobs.collectAsState()

    Scaffold(
        containerColor = DarkBlue
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text("Render & Generation Queue", style = MaterialTheme.typography.headlineSmall, color = PrimaryCyan, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
            }
            items(jobs.reversed()) { job ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = SurfaceBlue)
                ) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        when (job.status) {
                            JobStatus.COMPLETED -> Icon(Icons.Filled.CheckCircle, "Done", tint = SuccessGreen, modifier = Modifier.size(32.dp))
                            JobStatus.RUNNING -> Icon(Icons.Filled.Autorenew, "Running", tint = PrimaryCyan, modifier = Modifier.size(32.dp))
                            JobStatus.QUEUED -> Icon(Icons.Filled.Autorenew, "Queued", tint = TextMuted, modifier = Modifier.size(32.dp))
                            JobStatus.FAILED -> Icon(Icons.Filled.Autorenew, "Failed", tint = WarningOrange, modifier = Modifier.size(32.dp))
                        }
                        Spacer(modifier = Modifier.width(16.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(job.jobType, style = MaterialTheme.typography.titleMedium, color = TextLight)
                            Text("Target: ${job.targetType}", style = MaterialTheme.typography.bodySmall, color = TextMuted)
                            if (job.status == JobStatus.RUNNING) {
                                Spacer(modifier = Modifier.height(4.dp))
                                LinearProgressIndicator(
                                    progress = { job.progress / 100f },
                                    modifier = Modifier.fillMaxWidth(),
                                    color = PrimaryCyan
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AddProjectDialog(
    onDismiss: () -> Unit,
    onAdd: (String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var desc by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = SurfaceBlue,
        title = { Text("New Item", color = TextLight) },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextLight, unfocusedTextColor = TextLight,
                        focusedBorderColor = PrimaryCyan, unfocusedBorderColor = TextMuted
                    )
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = desc,
                    onValueChange = { desc = it },
                    label = { Text("Description (Optional)") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = TextLight, unfocusedTextColor = TextLight,
                        focusedBorderColor = PrimaryCyan, unfocusedBorderColor = TextMuted
                    )
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onAdd(name, desc) }) { Text("Create", color = PrimaryCyan) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = TextMuted) }
        }
    )
}
