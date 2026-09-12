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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.data.remote.BackendJob
import com.example.data.remote.NetworkClient
import com.example.data.remote.ProviderRunModel
import com.example.data.remote.WorkerData
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun ControlCenterScreen() {
    val context = LocalContext.current
    var jobs by remember { mutableStateOf<List<BackendJob>>(emptyList()) }
    var worker by remember { mutableStateOf<WorkerData?>(null) }
    var backendOk by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var selectedJobId by remember { mutableStateOf<String?>(null) }
    var selectedRuns by remember { mutableStateOf<List<ProviderRunModel>>(emptyList()) }
    var apiBaseUrl by remember { mutableStateOf(NetworkClient.getConfiguredBaseUrl(context)) }
    val scope = rememberCoroutineScope()

    suspend fun refresh() {
        try {
            val api = NetworkClient.apiService
            val health = api.health()
            jobs = api.listJobs(limit = 100).data
            worker = api.workerStatus().data
            backendOk = health.status.equals("ok", ignoreCase = true) || health.data.status.equals("OK", ignoreCase = true)
            selectedJobId?.let { id ->
                selectedRuns = runCatching { api.getProviderRuns(id, limit = 20).data }.getOrDefault(emptyList())
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
            delay(5000)
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Control Center", style = MaterialTheme.typography.headlineMedium)

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Backend connection", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = apiBaseUrl,
                    onValueChange = { apiBaseUrl = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text("Backend URL") },
                    placeholder = { Text("http://192.168.1.10:8000/") },
                    supportingText = { Text("Use the server LAN IP on a physical phone; 10.0.2.2 is emulator-only.") },
                )
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    Button(onClick = {
                        scope.launch {
                            try {
                                NetworkClient.setBaseUrl(context, apiBaseUrl)
                                refresh()
                            } catch (t: Throwable) {
                                backendOk = false
                                error = t.message ?: "Invalid backend URL"
                            }
                        }
                    }) { Text("Save & test") }
                }
            }
        }

        Text(if (backendOk) "Backend: ONLINE" else "Backend: OFFLINE", color = if (backendOk) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
        worker?.let { Text("Worker: ${it.workerId} · ${if (it.running) "RUNNING" else "STOPPED"} · iterations ${it.iterations}") }
        worker?.lastError?.let { Text("Worker error: $it", color = MaterialTheme.colorScheme.error) }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Text("Jobs (${jobs.size})", style = MaterialTheme.typography.titleLarge)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(jobs, key = { it.id }) { job ->
                ControlCenterJobCard(
                    job = job,
                    selected = selectedJobId == job.id,
                    runs = if (selectedJobId == job.id) selectedRuns else emptyList(),
                    onSelect = {
                        selectedJobId = if (selectedJobId == job.id) null else job.id
                        if (selectedJobId == job.id) {
                            scope.launch {
                                selectedRuns = runCatching { NetworkClient.apiService.getProviderRuns(job.id, 20).data }.getOrDefault(emptyList())
                            }
                        } else selectedRuns = emptyList()
                    },
                    onCancel = {
                        scope.launch {
                            try { NetworkClient.apiService.cancelJob(job.id); refresh() }
                            catch (t: Throwable) { error = t.message ?: "Cancel failed" }
                        }
                    },
                    onRetry = {
                        scope.launch {
                            try { NetworkClient.apiService.retryJob(job.id); refresh() }
                            catch (t: Throwable) { error = t.message ?: "Retry failed" }
                        }
                    },
                )
            }
        }
    }
}

@Composable
private fun ControlCenterJobCard(
    job: BackendJob,
    selected: Boolean,
    runs: List<ProviderRunModel>,
    onSelect: () -> Unit,
    onCancel: () -> Unit,
    onRetry: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth(), onClick = onSelect) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(job.type, style = MaterialTheme.typography.titleMedium)
            Text("${job.status} · ${job.projectId}")
            LinearProgressIndicator(progress = { job.progress.coerceIn(0.0, 1.0).toFloat() }, modifier = Modifier.fillMaxWidth())
            Text("Progress ${(job.progress * 100).toInt()}% · Attempt ${job.attempt}/${job.maxAttempts}")
            job.errorCode?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
            job.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                if (job.status in setOf("PENDING", "QUEUED", "RUNNING", "RETRYING")) Button(onClick = onCancel) { Text("Cancel") }
                if (job.status == "FAILED") Button(onClick = onRetry) { Text("Retry") }
            }

            if (selected) {
                Text("Provider Runs (${runs.size})", style = MaterialTheme.typography.labelLarge)
                runs.take(5).forEach { run ->
                    val duration = run.durationMs?.let { " · ${it}ms" } ?: ""
                    Text("${run.provider}${run.model?.let { "/$it" } ?: ""} · ${run.status}$duration")
                    run.errorCode?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
}
