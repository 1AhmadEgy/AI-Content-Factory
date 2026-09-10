package com.example.feature

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.core.theme.DarkBlue
import com.example.core.theme.PrimaryCyan
import com.example.core.theme.SurfaceBlue
import com.example.core.theme.TextLight
import com.example.core.theme.TextMuted
import com.example.data.remote.SeriesContext
import com.example.data.remote.SeriesTemplate
import com.example.data.remote.NetworkClient
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SeriesControlScreen(
    projectId: String,
    onBack: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    var templates by remember { mutableStateOf<List<SeriesTemplate>>(emptyList()) }
    var context by remember { mutableStateOf<SeriesContext?>(null) }
    var selectedTemplate by remember { mutableStateOf<String?>(null) }
    var title by remember { mutableStateOf("") }
    var factText by remember { mutableStateOf("") }
    var gagText by remember { mutableStateOf("") }
    var threadText by remember { mutableStateOf("") }
    var snapshots by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var message by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            try {
                val api = NetworkClient.apiService
                templates = api.listSeriesTemplates().data
                context = runCatching { api.getSeriesContext(projectId).data }.getOrNull()
                snapshots = runCatching { api.listSeriesSnapshots(projectId).data }.getOrDefault(emptyList())
                title = context?.title.orEmpty()
                selectedTemplate = context?.templateId
                message = null
            } catch (t: Throwable) {
                message = t.message ?: "تعذر تحميل بيانات المسلسل"
            }
        }
    }

    LaunchedEffect(projectId) { refresh() }

    fun applyTemplate(templateId: String) {
        scope.launch {
            try {
                context = NetworkClient.apiService.applySeriesTemplate(
                    projectId,
                    com.example.data.remote.ApplySeriesTemplateRequest(templateId, title.ifBlank { null })
                ).data
                selectedTemplate = templateId
                message = "تم تطبيق القالب مع الحفاظ على البيانات الموجودة"
            } catch (t: Throwable) {
                message = t.message ?: "فشل تطبيق القالب"
            }
        }
    }

    fun saveContext() {
        val current = context ?: return
        scope.launch {
            try {
                val facts = current.facts.toMutableList()
                if (factText.isNotBlank()) facts += mapOf("text" to factText.trim(), "source" to "android")
                val gags = current.runningGags.toMutableList()
                if (gagText.isNotBlank()) gags += mapOf("text" to gagText.trim(), "source" to "android")
                val threads = current.openThreads.toMutableList()
                if (threadText.isNotBlank()) threads += mapOf("text" to threadText.trim(), "source" to "android", "status" to "open")
                val updated = current.copy(
                    title = title.ifBlank { current.title },
                    facts = facts,
                    runningGags = gags,
                    openThreads = threads,
                )
                context = NetworkClient.apiService.patchSeriesContext(
                    projectId,
                    com.example.data.remote.SeriesContextPatchRequest(
                        mapOf(
                            "title" to updated.title,
                            "characters" to updated.characters,
                            "locations" to updated.locations,
                            "relationships" to updated.relationships,
                            "facts" to updated.facts,
                            "runningGags" to updated.runningGags,
                            "openThreads" to updated.openThreads,
                            "importantProps" to updated.importantProps,
                            "timeline" to updated.timeline,
                            "rules" to updated.rules,
                        )
                    )
                ).data
                factText = ""
                gagText = ""
                threadText = ""
                message = "تم حفظ الاستمرارية دون حذف السجل السابق"
            } catch (t: Throwable) {
                message = t.message ?: "فشل حفظ الاستمرارية"
            }
        }
    }

    fun snapshotEpisode() {
        scope.launch {
            message = "Snapshot يتم إنشاؤه تلقائيًا عند إنشاء الحلقة من مسار الإنتاج."
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("استمرارية المسلسل", color = TextLight) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع", tint = TextLight)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue)
            )
        },
        containerColor = DarkBlue,
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Text("Series ID: $projectId", color = TextMuted)
                Spacer(Modifier.height(4.dp))
                context?.let { c ->
                    Text("الحلقة التالية: ${c.nextEpisodeNumber}", style = MaterialTheme.typography.titleMedium, color = PrimaryCyan)
                    Text("النوع: ${c.genre} · القالب: ${c.templateId}", color = TextMuted)
                }
                message?.let { Text(it, color = PrimaryCyan) }
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("قوالب المسلسلات", style = MaterialTheme.typography.titleLarge, color = TextLight)
                        templates.forEach { template ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Column(Modifier.weight(1f)) {
                                    Text(template.name, color = TextLight)
                                    Text("${template.genre} · ${template.format}", color = TextMuted)
                                }
                                if (selectedTemplate == template.id) {
                                    Text("مفعّل", color = PrimaryCyan)
                                } else {
                                    OutlinedButton(onClick = { applyTemplate(template.id) }) { Text("تطبيق") }
                                }
                            }
                        }
                    }
                }
            }

            item {
                OutlinedTextField(value = title, onValueChange = { title = it }, label = { Text("اسم المسلسل") }, modifier = Modifier.fillMaxWidth())
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("ذاكرة الاستمرارية", style = MaterialTheme.typography.titleLarge, color = TextLight)
                        context?.let { c ->
                            Text("شخصيات: ${c.characters.size} · مواقع: ${c.locations.size}", color = TextMuted)
                            Text("حقائق: ${c.facts.size} · نكات متكررة: ${c.runningGags.size} · خيوط مفتوحة: ${c.openThreads.size}", color = TextMuted)
                            Text("علاقات: ${c.relationships.size} · عناصر مهمة: ${c.importantProps.size}", color = TextMuted)
                            Text("القواعد: ${c.rules.keys.joinToString().ifBlank { "افتراضية" }}", color = TextMuted)
                        }
                    }
                }
            }

            item { OutlinedTextField(value = factText, onValueChange = { factText = it }, label = { Text("إضافة حقيقة ثابتة") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(value = gagText, onValueChange = { gagText = it }, label = { Text("إضافة نكتة/لازمة متكررة") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(value = threadText, onValueChange = { threadText = it }, label = { Text("إضافة خيط قصة مفتوح") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { saveContext() }, modifier = Modifier.weight(1f)) { Text("حفظ الذاكرة") }
                    OutlinedButton(onClick = { refresh() }, modifier = Modifier.weight(1f)) { Text("تحديث") }
                }
            }

            item {
                Text("السجل التاريخي (${snapshots.size})", style = MaterialTheme.typography.titleLarge, color = PrimaryCyan)
            }
            items(snapshots.take(50)) { snapshot ->
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp)) {
                        Text("الحلقة ${snapshot["episodeNumber"] ?: "?"}", color = TextLight)
                        Text("Episode ID: ${snapshot["episodeId"] ?: "?"}", color = TextMuted)
                        Text("تم تثبيت نسخ الشخصيات/المواقع لهذه الحلقة", color = TextMuted)
                    }
                }
            }

            item {
                OutlinedButton(onClick = { snapshotEpisode() }, modifier = Modifier.fillMaxWidth()) {
                    Text("Snapshot / تثبيت سياق الحلقة")
                }
            }
        }
    }
}
