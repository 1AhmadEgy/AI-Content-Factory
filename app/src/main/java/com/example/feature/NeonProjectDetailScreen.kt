package com.example.feature

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.core.theme.*

@Composable
fun NeonProjectDetailScreen(projectId: String, viewModel: FactoryViewModel, onBack: () -> Unit, onSeriesClick: (String) -> Unit, onSeriesControlClick: () -> Unit) {
    val projects by viewModel.projects.collectAsState(); val allSeries by viewModel.series.collectAsState(); val project = projects.find { it.id == projectId }; val series = allSeries.filter { it.projectId == projectId }; var showDialog by remember { mutableStateOf(false) }
    Scaffold(containerColor = DarkBlue, floatingActionButton = { FloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan, contentColor = DarkBlue) { Icon(Icons.Default.Add, "إضافة مسلسل") } }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            item { TextButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, null, tint = PrimaryCyan); Spacer(Modifier.width(6.dp)); Text("رجوع", color = PrimaryCyan) } }
            item { NeonHero(project?.name ?: "المشروع", "مساحة الإنتاج · ${series.size} مسلسلات") }
            item { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text("المسلسلات", color = PrimaryCyan, style = MaterialTheme.typography.titleMedium); TextButton(onClick = onSeriesControlClick) { Text("التحكم بالمسلسل", color = PrimaryCyan) } } }
            if (series.isEmpty()) item { NeonSectionCard { Text("لا توجد مسلسلات بعد", color = TextLight, style = MaterialTheme.typography.titleMedium); Text("أنشئ مسلسلًا لبدء بناء الحلقات والمشاهد.", color = TextMuted); Button(onClick = { showDialog = true }, colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { Text("إنشاء مسلسل") } } }
            items(series, key = { it.id }) { item -> NeonSectionCard(Modifier.clickable { onSeriesClick(item.id) }) { Row(verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Filled.Movie, null, tint = PrimaryCyan, modifier = Modifier.size(28.dp)); Spacer(Modifier.width(12.dp)); Column(Modifier.weight(1f)) { Text(item.title, color = TextLight, style = MaterialTheme.typography.titleMedium); Text("التصنيف: ${item.genre ?: "غير محدد"}", color = TextMuted) }; NeonStatusChip("مفتوح") } } }
        }
        if (showDialog) AddProjectDialog(onDismiss = { showDialog = false }, onAdd = { name, _ -> viewModel.addSeries(projectId, name); showDialog = false })
    }
}
