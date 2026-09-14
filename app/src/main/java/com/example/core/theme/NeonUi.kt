package com.example.core.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.dp

@Composable
fun NeonSectionCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = SurfaceBlue)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

@Composable
fun NeonHero(title: String, subtitle: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth(), shape = RoundedCornerShape(26.dp), colors = CardDefaults.cardColors(containerColor = SurfaceBlue)) {
        Box(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(DarkBlue, SurfaceBlue, DarkBlue))).padding(20.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("AI CONTENT FACTORY", color = PrimaryCyan, style = MaterialTheme.typography.labelMedium)
                Text(title, color = TextLight, style = MaterialTheme.typography.headlineSmall)
                Text(subtitle, color = TextMuted, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
fun NeonStatusChip(text: String, active: Boolean = true) {
    AssistChip(onClick = {}, label = { Text(text) }, colors = AssistChipDefaults.assistChipColors(
        containerColor = if (active) PrimaryCyan.copy(alpha = 0.12f) else WarningOrange.copy(alpha = 0.12f),
        labelColor = if (active) PrimaryCyan else WarningOrange,
    ))
}

@Composable
fun NeonLoading() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = PrimaryCyan) }
}
