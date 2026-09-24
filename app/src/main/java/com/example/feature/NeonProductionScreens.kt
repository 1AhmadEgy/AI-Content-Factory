package com.example.feature

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.core.theme.*

@Composable private fun ProductionTopBar(title: String, subtitle: String, onBack: () -> Unit) { Surface(color = DarkBlue) { Row(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع", tint = TextLight) }; Column(Modifier.weight(1f)) { Text(title, color = TextLight, style = MaterialTheme.typography.titleLarge); Text(subtitle, color = TextMuted, style = MaterialTheme.typography.labelSmall) }; Icon(Icons.Filled.AutoAwesome, null, tint = PrimaryCyan) } } }

@Composable fun NeonSeriesDetailScreen(seriesId: String, viewModel: FactoryViewModel, onBack: () -> Unit, onEpisodeClick: (String) -> Unit) {
    val series by viewModel.series.collectAsState(); val episodes by viewModel.episodes.collectAsState(); val current = series.find { it.id == seriesId }; val list = episodes.filter { it.seriesId == seriesId }.sortedBy { it.number }; var showDialog by remember { mutableStateOf(false) }
    Scaffold(topBar = { ProductionTopBar(current?.title ?: "المسلسل", "مساحة عمل المسلسل", onBack) }, floatingActionButton = { ExtendedFloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan, contentColor = DarkBlue, icon = { Icon(Icons.Filled.Add, null) }, text = { Text("إضافة حلقة") }) }, containerColor = DarkBlue) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp, 8.dp, 16.dp, 96.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) { item { NeonHeroCard(current?.title ?: "المسلسل", "مساحة إنتاج الحلقات", "${list.size} حلقات") }; items(list, key = { it.id }) { ep -> Card(Modifier.fillMaxWidth().clickable { onEpisodeClick(ep.id) }, colors = CardDefaults.cardColors(SurfaceBlue), shape = RoundedCornerShape(20.dp)) { Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) { Surface(Modifier.size(52.dp), RoundedCornerShape(16.dp), color = DarkBlue) { Box(contentAlignment = Alignment.Center) { Text(ep.number.toString(), color = PrimaryCyan, style = MaterialTheme.typography.titleLarge) } }; Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(ep.title, color = TextLight, style = MaterialTheme.typography.titleMedium); Text("الحلقة ${ep.number} · ${if (ep.status == "DONE") "مكتملة" else ep.status}", color = TextMuted, style = MaterialTheme.typography.bodySmall) }; Icon(Icons.Filled.PlayArrow, null, tint = PrimaryCyan) } } } }
        if (showDialog) AddProjectDialog({ showDialog = false }, { name, _ -> viewModel.addEpisode(seriesId, (list.maxOfOrNull { it.number } ?: 0) + 1, name); showDialog = false })
    }
}

@Composable fun NeonEpisodeDetailScreen(episodeId: String, viewModel: FactoryViewModel, onBack: () -> Unit) {
    val episodes by viewModel.episodes.collectAsState(); val scenes by viewModel.scenes.collectAsState(); val jobs by viewModel.jobs.collectAsState(); val episode = episodes.find { it.id == episodeId }; val list = scenes.filter { it.episodeId == episodeId }.sortedBy { it.number }
    Scaffold(topBar = { ProductionTopBar(episode?.title ?: "الحلقة", "إنتاج المشاهد", onBack) }, containerColor = DarkBlue) { padding -> LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) { item { NeonHeroCard(episode?.title ?: "الحلقة", "إنشاء ومتابعة كل مشهد", "${list.size} مشاهد") }; items(list, key = { it.id }) { scene -> val job = jobs.find { it.targetId == scene.id }; Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(SurfaceBlue), shape = RoundedCornerShape(20.dp)) { Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { Row(verticalAlignment = Alignment.CenterVertically) { Text("المشهد ${scene.number}", color = PrimaryCyan, style = MaterialTheme.typography.labelLarge); Spacer(Modifier.weight(1f)); Text(if (scene.status == "DONE") "مكتمل" else scene.status, color = if (scene.status == "DONE") SuccessGreen else WarningOrange) }; Text(scene.description, color = TextLight, style = MaterialTheme.typography.titleMedium); Text("الموقع: ${scene.location}", color = TextMuted); Text("المشاعر: ${scene.emotion}", color = TextMuted); job?.let { Text("المهمة: ${it.status} · ${it.progress}%", color = PrimaryCyan) }; Button(onClick = { viewModel.generateScene(scene.id) }, colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue), shape = RoundedCornerShape(14.dp)) { Icon(Icons.Filled.PlayArrow, null); Spacer(Modifier.width(6.dp)); Text("إنشاء", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold) } } } } } }
}

@Composable private fun NeonHeroCard(title: String, subtitle: String, metric: String) { Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(SurfaceBlue), shape = RoundedCornerShape(26.dp)) { Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { Row(verticalAlignment = Alignment.CenterVertically) { Surface(Modifier.size(44.dp), RoundedCornerShape(14.dp), color = PrimaryCyan) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.Movie, null, tint = DarkBlue) } }; Spacer(Modifier.width(12.dp)); Column { Text(title, color = TextLight, style = MaterialTheme.typography.titleLarge); Text(subtitle, color = TextMuted, style = MaterialTheme.typography.bodySmall) } }; HorizontalDivider(color = TextMuted.copy(alpha = .12f)); Text(metric, color = SecondaryTeal, style = MaterialTheme.typography.labelLarge) } } }
