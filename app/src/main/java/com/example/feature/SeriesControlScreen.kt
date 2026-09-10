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
import com.example.data.remote.ApplySeriesTemplateRequest
import com.example.data.remote.CountryLibrary
import com.example.data.remote.LanguageInfo
import com.example.data.remote.NetworkClient
import com.example.data.remote.SeriesContext
import com.example.data.remote.SeriesTemplate
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SeriesControlScreen(projectId: String, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    var templates by remember { mutableStateOf<List<SeriesTemplate>>(emptyList()) }
    var countries by remember { mutableStateOf<List<CountryLibrary>>(emptyList()) }
    var languages by remember { mutableStateOf<List<LanguageInfo>>(emptyList()) }
    var context by remember { mutableStateOf<SeriesContext?>(null) }
    var selectedTemplate by remember { mutableStateOf<String?>(null) }
    var selectedCountry by remember { mutableStateOf("egypt") }
    var sourceLanguage by remember { mutableStateOf("ar") }
    var targetLanguages by remember { mutableStateOf<List<String>>(emptyList()) }
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
                countries = api.listCountryLibraries().data
                context = runCatching { api.getSeriesContext(projectId).data }.getOrNull()
                snapshots = runCatching { api.listSeriesSnapshots(projectId).data }.getOrDefault(emptyList())
                val current = context
                title = current?.title.orEmpty()
                selectedTemplate = current?.templateId
                selectedCountry = current?.countryId ?: "egypt"
                sourceLanguage = current?.sourceLanguage ?: "ar"
                targetLanguages = current?.targetLanguages ?: emptyList()
                languages = runCatching { api.getCountryLanguages(selectedCountry).data }.getOrDefault(emptyList())
                message = null
            } catch (t: Throwable) {
                message = t.message ?: "تعذر تحميل بيانات المسلسل"
            }
        }
    }

    LaunchedEffect(projectId) { refresh() }

    fun selectCountry(countryId: String) {
        scope.launch {
            try {
                selectedCountry = countryId
                val api = NetworkClient.apiService
                languages = api.getCountryLanguages(countryId).data
                val country = countries.firstOrNull { it.id == countryId }
                sourceLanguage = country?.defaultLanguage ?: languages.firstOrNull()?.id ?: sourceLanguage
                targetLanguages = listOf(sourceLanguage)
                message = "تم اختيار مكتبة ${country?.name ?: countryId}"
            } catch (t: Throwable) {
                message = t.message ?: "تعذر تحميل لغات المكتبة"
            }
        }
    }

    fun toggleTargetLanguage(languageId: String) {
        targetLanguages = if (languageId in targetLanguages) targetLanguages - languageId else targetLanguages + languageId
    }

    fun applyTemplate(templateId: String) {
        scope.launch {
            try {
                context = NetworkClient.apiService.applySeriesTemplate(
                    projectId,
                    ApplySeriesTemplateRequest(templateId, title.ifBlank { null }, selectedCountry, sourceLanguage, targetLanguages, context?.dialect)
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
                val updated = NetworkClient.apiService.patchSeriesContext(projectId, com.example.data.remote.SeriesContextPatchRequest(mapOf(
                    "title" to title.ifBlank { current.title },
                    "countryId" to selectedCountry,
                    "libraryId" to (countries.firstOrNull { it.id == selectedCountry }?.libraryId ?: current.libraryId),
                    "sourceLanguage" to sourceLanguage,
                    "targetLanguages" to targetLanguages.distinct(),
                    "dialect" to current.dialect,
                    "translationPolicy" to current.translationPolicy,
                    "glossary" to current.glossary,
                    "translationVersions" to current.translationVersions,
                    "characters" to current.characters,
                    "locations" to current.locations,
                    "relationships" to current.relationships,
                    "facts" to facts,
                    "runningGags" to gags,
                    "openThreads" to threads,
                    "importantProps" to current.importantProps,
                    "timeline" to current.timeline,
                    "rules" to current.rules,
                ))).data
                context = updated
                factText = ""; gagText = ""; threadText = ""
                message = "تم حفظ الإعدادات والذاكرة دون حذف السجل السابق"
            } catch (t: Throwable) {
                message = t.message ?: "فشل حفظ الاستمرارية"
            }
        }
    }

    Scaffold(topBar = {
        TopAppBar(title = { Text("استمرارية المسلسل", color = TextLight) }, navigationIcon = {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع", tint = TextLight) }
        }, colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBlue))
    }, containerColor = DarkBlue) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            item {
                Text("Series ID: $projectId", color = TextMuted)
                context?.let { Text("الحلقة التالية: ${it.nextEpisodeNumber} · ${it.genre}", style = MaterialTheme.typography.titleMedium, color = PrimaryCyan) }
                message?.let { Text(it, color = PrimaryCyan) }
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("مكتبة الدولة واللغات", style = MaterialTheme.typography.titleLarge, color = TextLight)
                        Text("اختر مكتبة مستقلة. المحتوى لا يختلط بين الدول.", color = TextMuted)
                        countries.forEach { country ->
                            OutlinedButton(onClick = { selectCountry(country.id) }, modifier = Modifier.fillMaxWidth()) {
                                Text(if (country.id == selectedCountry) "✓ ${country.name}" else country.name)
                            }
                        }
                        Text("لغة المصدر: $sourceLanguage", color = TextMuted)
                        languages.forEach { language ->
                            OutlinedButton(onClick = { sourceLanguage = language.id }, modifier = Modifier.fillMaxWidth()) {
                                Text(if (language.id == sourceLanguage) "✓ المصدر: ${language.nativeName ?: language.name}" else "المصدر: ${language.nativeName ?: language.name}")
                            }
                        }
                        Text("لغات الإخراج: ${targetLanguages.joinToString().ifBlank { "نفس لغة المصدر" }}", color = TextMuted)
                        languages.forEach { language ->
                            OutlinedButton(onClick = { toggleTargetLanguage(language.id) }, modifier = Modifier.fillMaxWidth()) {
                                Text(if (language.id in targetLanguages) "✓ إخراج: ${language.nativeName ?: language.name}" else "إضافة إخراج: ${language.nativeName ?: language.name}")
                            }
                        }
                    }
                }
            }

            item {
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("قوالب المسلسلات", style = MaterialTheme.typography.titleLarge, color = TextLight)
                        templates.forEach { template ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Column(Modifier.weight(1f)) { Text(template.name, color = TextLight); Text("${template.genre} · ${template.format}", color = TextMuted) }
                                if (selectedTemplate == template.id) Text("مفعّل", color = PrimaryCyan) else OutlinedButton(onClick = { applyTemplate(template.id) }) { Text("تطبيق") }
                            }
                        }
                    }
                }
            }

            item { OutlinedTextField(value = title, onValueChange = { title = it }, label = { Text("اسم المسلسل") }, modifier = Modifier.fillMaxWidth()) }
            item {
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("ذاكرة الاستمرارية", style = MaterialTheme.typography.titleLarge, color = TextLight)
                        context?.let { c ->
                            Text("شخصيات: ${c.characters.size} · مواقع: ${c.locations.size}", color = TextMuted)
                            Text("حقائق: ${c.facts.size} · نكات: ${c.runningGags.size} · خيوط: ${c.openThreads.size}", color = TextMuted)
                            Text("البلد: ${c.countryId ?: "غير محدد"} · المصدر: ${c.sourceLanguage ?: "-"}", color = TextMuted)
                            Text("الإخراج: ${c.targetLanguages.joinToString().ifBlank { "-" }}", color = TextMuted)
                        }
                    }
                }
            }
            item { OutlinedTextField(value = factText, onValueChange = { factText = it }, label = { Text("إضافة حقيقة ثابتة") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(value = gagText, onValueChange = { gagText = it }, label = { Text("إضافة نكتة/لازمة متكررة") }, modifier = Modifier.fillMaxWidth()) }
            item { OutlinedTextField(value = threadText, onValueChange = { threadText = it }, label = { Text("إضافة خيط قصة مفتوح") }, modifier = Modifier.fillMaxWidth()) }
            item { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) { Button(onClick = { saveContext() }, Modifier.weight(1f)) { Text("حفظ") }; OutlinedButton(onClick = { refresh() }, Modifier.weight(1f)) { Text("تحديث") } } }
            item { Text("السجل التاريخي (${snapshots.size})", style = MaterialTheme.typography.titleLarge, color = PrimaryCyan) }
            items(snapshots.take(50)) { snapshot ->
                Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text("الحلقة ${snapshot["episodeNumber"] ?: "?"}", color = TextLight); Text("Episode ID: ${snapshot["episodeId"] ?: "?"}", color = TextMuted); Text("تم تثبيت نسخ الشخصيات والمواقع لهذه الحلقة", color = TextMuted) } }
            }
        }
    }
}
