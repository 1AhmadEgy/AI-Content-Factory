package com.example.feature

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.core.theme.*
import com.example.data.remote.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun NeonControlCenterScreen() {
    var jobs by remember { mutableStateOf<List<BackendJob>>(emptyList()) }
    var worker by remember { mutableStateOf<WorkerData?>(null) }
    var online by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf<String?>(null) }
    var runs by remember { mutableStateOf<List<ProviderRunModel>>(emptyList()) }
    val scope = rememberCoroutineScope()
    suspend fun refresh() = runCatching {
        val api = NetworkClient.apiService; val health = api.health()
        jobs = api.listJobs(limit = 100).data; worker = api.workerStatus().data
        online = health.status.equals("ok", true) || health.data.status.equals("OK", true)
        selected?.let { runs = runCatching { api.getProviderRuns(it, 20).data }.getOrDefault(emptyList()) }
        error = null
    }.onFailure { online = false; error = it.message ?: "Backend unavailable" }
    LaunchedEffect(Unit) { while (true) { refresh(); delay(5000) } }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), contentPadding = PaddingValues(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { NeonHero("Control Center", "Real-time command center for backend health, workers, jobs and AI providers.") }
        item { NeonSectionCard {
            Text("SYSTEM STATUS", color = PrimaryCyan, style = MaterialTheme.typography.labelMedium)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (online) "BACKEND ONLINE" else "BACKEND OFFLINE", color = if (online) SuccessGreen else MaterialTheme.colorScheme.error, style = MaterialTheme.typography.titleMedium)
                worker?.let { NeonStatusChip(if (it.running) "WORKER RUNNING" else "WORKER STOPPED", it.running) }
            }
            worker?.let { Text("${it.workerId} · ${it.iterations} iterations", color = TextMuted) }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        } }
        item { Text("JOBS  •  ${jobs.size}", color = PrimaryCyan, style = MaterialTheme.typography.titleMedium) }
        items(jobs, key = { it.id }) { job ->
            NeonSectionCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Column(Modifier.weight(1f)) { Text(job.type, color = TextLight, style = MaterialTheme.typography.titleMedium); Text(job.projectId, color = TextMuted) }; NeonStatusChip(job.status, job.status !in setOf("FAILED", "CANCELLED")) }
                LinearProgressIndicator(progress = { job.progress.coerceIn(0.0, 1.0).toFloat() }, Modifier.fillMaxWidth(), color = PrimaryCyan, trackColor = DarkBlue)
                Text("${(job.progress * 100).toInt()}% · attempt ${job.attempt}/${job.maxAttempts}", color = TextMuted)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { if (selected == job.id) { selected = null; runs = emptyList() } else { selected = job.id; scope.launch { runs = runCatching { NetworkClient.apiService.getProviderRuns(job.id, 20).data }.getOrDefault(emptyList()) } } }) { Text(if (selected == job.id) "Hide Runs" else "Provider Runs") }
                    if (job.status in setOf("PENDING", "QUEUED", "RUNNING", "RETRYING")) Button(onClick = { scope.launch { runCatching { NetworkClient.apiService.cancelJob(job.id); refresh() }.onFailure { error = it.message ?: "Cancel failed" } } }) { Text("Cancel") }
                    if (job.status == "FAILED") Button(onClick = { scope.launch { runCatching { NetworkClient.apiService.retryJob(job.id); refresh() }.onFailure { error = it.message ?: "Retry failed" } } }) { Text("Retry") }
                }
                if (selected == job.id) { Text("Provider Runs (${runs.size})", color = PrimaryCyan); runs.take(5).forEach { run -> Text("${run.provider}${run.model?.let { "/$it" } ?: ""} · ${run.status}", color = TextMuted) } }
            }
        }
    }
}
