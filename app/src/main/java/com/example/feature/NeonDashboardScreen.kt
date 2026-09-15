package com.example.feature

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CreateNewFolder
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.TextFields
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.model.Project
import com.example.core.theme.*

@Composable
fun NeonDashboardScreen(viewModel: FactoryViewModel, onProjectClick: (String) -> Unit) {
    val projects by viewModel.projects.collectAsState()
    var showDialog by remember { mutableStateOf(false) }
    Scaffold(containerColor = DarkBlue, floatingActionButton = {
        ExtendedFloatingActionButton(onClick = { showDialog = true }, containerColor = PrimaryCyan, contentColor = DarkBlue, shape = RoundedCornerShape(18.dp), icon = { Icon(Icons.Filled.CreateNewFolder, null) }, text = { Text("مشروع جديد", fontWeight = FontWeight.ExtraBold) })
    }) { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp, 14.dp, 16.dp, 104.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item { NeonHero(projects.size) { showDialog = true } }
            item { QuickToolsSection() }
            item { Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) { Column(Modifier.weight(1f)) { Text("مشاريعك", color = TextLight, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold); Text("إدارة مساحة عمل الإنتاج الإبداعي", color = TextMuted, style = MaterialTheme.typography.bodySmall) }; Text("${projects.size} إجماليًا", color = PrimaryCyan, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold) } }
            if (projects.isEmpty()) item { NeonEmptyState { showDialog = true } } else items(projects) { project -> NeonProjectCard(project) { onProjectClick(project.id) } }
        }
        if (showDialog) AddProjectDialog(onDismiss = { showDialog = false }, onAdd = { name, desc -> viewModel.addProject(name, desc); showDialog = false })
    }
}

@Composable
private fun NeonHero(projectCount: Int, onCreate: () -> Unit) {
    Card(shape = RoundedCornerShape(28.dp), colors = CardDefaults.cardColors(containerColor = SurfaceBlue), modifier = Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(SurfaceBlue, DarkBlue, SurfaceBlue))).padding(22.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(13.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(shape = RoundedCornerShape(17.dp), color = PrimaryCyan.copy(alpha = .14f), modifier = Modifier.size(54.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.AutoAwesome, null, tint = PrimaryCyan, modifier = Modifier.size(31.dp)) } }
                    Spacer(Modifier.width(14.dp)); Column { Text("مصنع المحتوى بالذكاء الاصطناعي", color = PrimaryCyan, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.ExtraBold); Text("مركز القيادة الإبداعي", color = TextLight, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold) }
                }
                Text("أنشئ وعدّل ونظّم المحتوى المدعوم بالذكاء الاصطناعي من مساحة عمل واحدة.", color = TextMuted, style = MaterialTheme.typography.bodyMedium)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(onClick = onCreate, shape = RoundedCornerShape(15.dp), colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)) { Icon(Icons.Filled.CreateNewFolder, null); Spacer(Modifier.width(7.dp)); Text("إنشاء مشروع", fontWeight = FontWeight.ExtraBold) }
                    Surface(shape = RoundedCornerShape(15.dp), color = DarkBlue.copy(alpha = .8f)) { Row(Modifier.padding(horizontal = 13.dp, vertical = 11.dp), verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Filled.Folder, null, tint = SecondaryTeal, modifier = Modifier.size(19.dp)); Spacer(Modifier.width(7.dp)); Text("$projectCount مشروع", color = TextLight, fontWeight = FontWeight.Bold) } }
                }
            }
        }
    }
}

@Composable
private fun QuickToolsSection() {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Filled.AutoAwesome, null, tint = SecondaryTeal, modifier = Modifier.size(23.dp)); Spacer(Modifier.width(8.dp)); Column { Text("أدوات سريعة", color = TextLight, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold); Text("الوصول السريع إلى سير العمل الإبداعي", color = TextMuted, style = MaterialTheme.typography.bodySmall) } }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) { QuickToolCard(Modifier.weight(1f), Icons.Filled.Palette, "نص إلى صورة", "إنشاء صور", PrimaryCyan); QuickToolCard(Modifier.weight(1f), Icons.Filled.Movie, "نص إلى فيديو", "إنشاء مشاهد", SecondaryTeal); QuickToolCard(Modifier.weight(1f), Icons.Filled.TextFields, "محرر ذكي", "تحسين المحتوى", WarningOrange) }
    }
}

@Composable
private fun QuickToolCard(modifier: Modifier, icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, subtitle: String, accent: androidx.compose.ui.graphics.Color) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = SurfaceBlue), shape = RoundedCornerShape(18.dp)) { Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) { Surface(shape = RoundedCornerShape(11.dp), color = accent.copy(alpha = .14f), modifier = Modifier.size(38.dp)) { Box(contentAlignment = Alignment.Center) { Icon(icon, null, tint = accent, modifier = Modifier.size(21.dp)) } }; Text(title, color = TextLight, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.ExtraBold); Text(subtitle, color = TextMuted, style = MaterialTheme.typography.labelSmall, maxLines = 1) } }
}

@Composable
private fun NeonProjectCard(project: Project, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick), colors = CardDefaults.cardColors(containerColor = SurfaceBlue), shape = RoundedCornerShape(21.dp)) { Column(Modifier.padding(17.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) { Row(verticalAlignment = Alignment.CenterVertically) { Surface(shape = RoundedCornerShape(13.dp), color = DarkBlue) { Icon(Icons.Filled.Movie, null, tint = PrimaryCyan, modifier = Modifier.padding(10.dp).size(23.dp)) }; Spacer(Modifier.width(11.dp)); Column(Modifier.weight(1f)) { Text(project.name, color = TextLight, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold); Text("مشروع إنتاج بالذكاء الاصطناعي", color = TextMuted, style = MaterialTheme.typography.labelSmall) }; Text(if (project.status == "ACTIVE") "نشط" else "قيد الانتظار", color = if (project.status == "ACTIVE") SuccessGreen else WarningOrange, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold) }; Text(project.description ?: "لا يوجد وصف", color = TextMuted, style = MaterialTheme.typography.bodyMedium); HorizontalDivider(color = TextMuted.copy(alpha = .13f)); Row(verticalAlignment = Alignment.CenterVertically) { Text("فتح مساحة العمل", color = PrimaryCyan, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.ExtraBold); Spacer(Modifier.weight(1f)); Icon(Icons.Filled.PlayArrow, null, tint = PrimaryCyan) } } }
}

@Composable
private fun NeonEmptyState(onCreate: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = SurfaceBlue), shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.fillMaxWidth().padding(30.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) { Surface(shape = RoundedCornerShape(18.dp), color = PrimaryCyan.copy(alpha = .12f), modifier = Modifier.size(66.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.AutoAwesome, null, tint = PrimaryCyan, modifier = Modifier.size(34.dp)) } }; Text("مساحة العمل الإبداعية جاهزة", color = TextLight, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold); Text("ابدأ أول مشروع للذكاء الاصطناعي وحوّل أفكارك إلى إنتاج.", color = TextMuted, style = MaterialTheme.typography.bodyMedium); Button(onClick = onCreate, colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue), shape = RoundedCornerShape(14.dp)) { Text("ابدأ الإنشاء", fontWeight = FontWeight.ExtraBold) } } }
}
