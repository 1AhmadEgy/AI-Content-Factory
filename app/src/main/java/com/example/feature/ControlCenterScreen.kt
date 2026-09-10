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
import com.example.data.remote.JobEvent
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
    var selectedJobId by remember { mutableStateOf<String?>(null) }
    var selectedEvents by remember { mutableStateOf<List<JobEvent>>(emptyList()) }
    var recovered by remember { mutableStateOf<Int?>(null) }
    val scope = rememberCoroutineScope()

    suspend fun refresh() {
        try {
            val api = NetworkClient.apiService
            val health = api.health()
            jobs = api.listJobs(limit = 100).data
            worker = api.workerStatus().data
            backendOk = health.data.status.equals("ok", ignoreCase = true) || health.status.equals("ok", ignoreCase = true)
            selectedJobId?.let { id ->
                selectedEvents = api.jobEvents(id, limit = 100).data
            }
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
        Text(
            if (backendOk) "Backend: ONLINE" else "Backend: OFFLINE",
            color = if (backendOk) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
        )
        worker?.let {
            Text("Worker: ${it.workerId} · ${if (it.running) "RUNNING" else "STOPPED"} · iterations ${it.iterations}")
            it.lastError?.let { message -> Text("Worker error: $message", color = MaterialTheme.colorScheme.error) }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { scope.launch { refresh() } }) { Text("Refresh") }
            Button(onClick = {
                scope.launch {
                    try {
                        recovered = NetworkClient.apiService.recoverExpired().data.recovered
                        refresh()
                    } catch (t: Throwable) {
                        error = t.message ?: "Recovery failed"
                    }
                }
            }) { Text("Recover expired") }
        }
        recovered?.let { Text("Recovered: $it") }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        val running = jobs.count { it.status in setOf("PENDING", "QUEUED", "RUNNING", "RETRYING") }
        val completed = jobs.count { it.status == "COMPLETED" }
        val failed = jobs.count { it.status == "FAILED" }
        Text("Jobs ${jobs.size} · Active $running · Completed $completed · Failed $failed", style = MaterialTheme.typography.titleLarge)

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(jobs, key = { it.id }) { job ->
                ControlCenterJobCard(
                    job = job,
                    selected = selectedJobId == job.id,
                    events = if (selectedJobId == job.id) selectedEvents else emptyList(),
                    onSelect = {
                        selectedJobId = if (selectedJobId == job.id) null else job.id
                        if (selectedJobId == job.id) {
                            scope.launch {
                                try { selectedEvents = NetworkClient.apiService.jobEvents(job.id, 100).data }
                                catch (t: Throwable) { error = t.message ?: "Unable to load events" }
                            }
                        } else selectedEvents = emptyList()
                    },
                    onCancel = {
                        scope.launch {
                            try {
                                NetworkClient.apiService.cancelJob(job.id)
                                refresh()
                            } catch (t: Throwable) { error = t.message ?: "Cancel failed" }
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun ControlCenterJobCard(
    job: BackendJob,
    selected: Boolean,
    events: List<JobEvent>,
    onSelect: () -> Unit,
    onCancel: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth(), onClick = onSelect) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(job.type, style = MaterialTheme.typography.titleMedium)
            Text("${job.status} · ${job.projectId}")
            job.provider?.let { provider -> Text("Provider: $provider${job.model?.let { " / $it" } ?: ""}") }
            LinearProgressIndicator(progress = { job.progress.coerceIn(0.0, 1.0).toFloat() }, modifier = Modifier.fillMaxWidth())
            Text("Progress ${(job.progress * 100).toInt()}% · Attempt ${job.attempt}/${job.maxAttempts}")
            job.errorCode?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
            job.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            if (job.status in setOf("PENDING", "QUEUED", "RUNNING", "RETRYING")) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    Button(onClick = onCancel) { Text("Cancel") }
                }
            }

            if (selected) {
                Text("Pipeline events", style = MaterialTheme.typography.titleSmall)
                if (events.isEmpty()) {
                    Text("No events yet")
                } else {
                    events.takeLast(20).forEach { event ->
                        val progress = event.progress?.let { " · ${(it.coerceIn(0.0, 1.0) * 100).toInt()}%" } ?: ""
                        Text("${event.eventType}${event.status?.let { " · $it" } ?: ""}$progress")
                    }
                }
            }
        }
    }
}
