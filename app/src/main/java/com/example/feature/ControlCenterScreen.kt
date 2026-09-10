package com.example.feature

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.data.remote.BackendJob
import com.example.data.remote.NetworkClient
import com.example.data.remote.WorkerData
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun ControlCenterScreen() {
    var jobs by remember { mutableStateOf<List<BackendJob>>(emptyList()) }
    var worker by remember { mutableStateOf<WorkerData?>(null) }
    var backendOk by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    suspend fun refresh() {
        try {
            val api = NetworkClient.apiService
            val health = api.health()
            jobs = api.listJobs(limit = 100).data
            worker = api.workerStatus().data
            backendOk = health.status.equals("ok", ignoreCase = true)
            error = null
        } catch (t: Throwable) {
            backendOk = false
            error = t.message ?: "Backend unavailable"
        }
    }

    LaunchedEffect(Unit) {
        while (true) {
            refresh()
            delay(3000)
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Control Center", style = MaterialTheme.typography.headlineMedium)
        Text(if (backendOk) "Backend: ONLINE" else "Backend: OFFLINE", color = if (backendOk) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
        worker?.let { Text("Worker: ${it.workerId} · ${if (it.running) "RUNNING" else "STOPPED"}") }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Text("Jobs (${jobs.size})", style = MaterialTheme.typography.titleLarge)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(jobs, key = { it.id }) { job ->
                ControlCenterJobCard(job) {
                    scope.launch { try { NetworkClient.apiService.cancelJob(job.id) } catch (_: Throwable) { } }
                }
            }
        }
    }
}

@Composable
private fun ControlCenterJobCard(job: BackendJob, onCancel: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(job.type, style = MaterialTheme.typography.titleMedium)
            Text("${job.status} · ${job.projectId}")
            LinearProgressIndicator(progress = { job.progress.coerceIn(0.0, 1.0).toFloat() }, modifier = Modifier.fillMaxWidth())
            Text("Progress ${(job.progress * 100).toInt()}% · Attempt ${job.attempt}/${job.maxAttempts}")
            if (job.errorMessage != null) Text(job.errorMessage, color = MaterialTheme.colorScheme.error)
            if (job.status in setOf("PENDING", "QUEUED", "RUNNING")) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    Button(onClick = onCancel) { Text("Cancel") }
                }
            }
        }
    }
}
