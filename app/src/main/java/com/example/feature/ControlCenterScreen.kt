package com.example.feature

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.data.remote.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private fun arabicStatus(status: String): String = when (status.uppercase()) {
    "PENDING" -> "قيد الانتظار"
    "QUEUED" -> "في قائمة الانتظار"
    "RUNNING" -> "قيد التنفيذ"
    "RETRYING" -> "إعادة المحاولة"
    "DONE", "COMPLETED", "SUCCESS", "SUCCEEDED" -> "مكتمل"
    "FAILED" -> "فشل"
    "CANCELLED", "CANCELED" -> "ملغى"
    "ACTIVE" -> "نشط"
    "PAUSED" -> "متوقف مؤقتًا"
    "STOPPED" -> "متوقف"
    else -> status
}

@Composable
fun ControlCenterScreen() {
    var jobs by remember { mutableStateOf<List<BackendJob>>(emptyList()) }
    var worker by remember { mutableStateOf<WorkerData?>(null) }
    var backendOk by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var selectedJobId by remember { mutableStateOf<String?>(null) }
    var selectedRuns by remember { mutableStateOf<List<ProviderRunModel>>(emptyList()) }
    val scope = rememberCoroutineScope()

    suspend fun refresh() {
        try {
            val api = NetworkClient.apiService
            val health = api.health()
            jobs = api.listJobs(limit = 100).data
            worker = api.workerStatus().data
            backendOk = health.status.equals("ok", ignoreCase = true) || health.data.status.equals("OK", ignoreCase = true)
            selectedJobId?.let { id -> selectedRuns = runCatching { api.getProviderRuns(id, limit = 20).data }.getOrDefault(emptyList()) }
            error = null
        } catch (t: Throwable) {
            backendOk = false
            error = t.message ?: "تعذر الاتصال بالخادم"
        }
    }

    LaunchedEffect(Unit) { while (true) { refresh(); delay(5000) } }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("مركز التحكم", style = MaterialTheme.typography.headlineMedium)
        Text(if (backendOk) "الخادم: متصل" else "الخادم: غير متصل", color = if (backendOk) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
        worker?.let { Text("العامل: ${it.workerId} · ${if (it.running) "يعمل" else "متوقف"} · عدد الدورات ${it.iterations}") }
        worker?.lastError?.let { Text("خطأ العامل: $it", color = MaterialTheme.colorScheme.error) }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Text("المهام (${jobs.size})", style = MaterialTheme.typography.titleLarge)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(jobs, key = { it.id }) { job ->
                Card(Modifier.fillMaxWidth(), onClick = {
                    selectedJobId = if (selectedJobId == job.id) null else job.id
                    if (selectedJobId == job.id) scope.launch { selectedRuns = runCatching { NetworkClient.apiService.getProviderRuns(job.id, 20).data }.getOrDefault(emptyList()) } else selectedRuns = emptyList()
                }) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(job.type, style = MaterialTheme.typography.titleMedium)
                        Text("${arabicStatus(job.status)} · ${job.projectId}")
                        LinearProgressIndicator(progress = { job.progress.coerceIn(0.0, 1.0).toFloat() }, Modifier.fillMaxWidth())
                        Text("التقدم ${(job.progress * 100).toInt()}% · المحاولة ${job.attempt}/${job.maxAttempts}")
                        job.errorCode?.let { Text("رمز الخطأ: $it", color = MaterialTheme.colorScheme.error) }
                        job.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                            if (job.status in setOf("PENDING", "QUEUED", "RUNNING", "RETRYING")) Button(onClick = { scope.launch { runCatching { NetworkClient.apiService.cancelJob(job.id); refresh() }.onFailure { error = it.message ?: "فشل الإلغاء" } } }) { Text("إلغاء") }
                            if (job.status == "FAILED") Button(onClick = { scope.launch { runCatching { NetworkClient.apiService.retryJob(job.id); refresh() }.onFailure { error = it.message ?: "فشلت إعادة المحاولة" } } }) { Text("إعادة المحاولة") }
                        }
                        if (selectedJobId == job.id) {
                            Text("تشغيلات المزود (${selectedRuns.size})", style = MaterialTheme.typography.labelLarge)
                            selectedRuns.take(5).forEach { run ->
                                val duration = run.durationMs?.let { " · ${it} مللي ثانية" } ?: ""
                                Text("${run.provider}${run.model?.let { "/$it" } ?: ""} · ${arabicStatus(run.status)}$duration")
                                run.errorCode?.let { Text("رمز الخطأ: $it", color = MaterialTheme.colorScheme.error) }
                            }
                        }
                    }
                }
            }
        }
    }
}
