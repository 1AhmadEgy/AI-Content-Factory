package com.example.core.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun NeonSectionCard(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceBlue),
        border = androidx.compose.foundation.BorderStroke(1.dp, BorderBlue.copy(alpha = .55f))
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

@Composable
fun NeonHero(title: String, subtitle: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth(), shape = RoundedCornerShape(26.dp), colors = CardDefaults.cardColors(containerColor = SurfaceBlue)) {
        Box(
            Modifier.fillMaxWidth()
                .background(Brush.linearGradient(listOf(DarkBlue, ElevatedBlue, SurfaceBlue)))
                .padding(20.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("AI CONTENT FACTORY", color = PrimaryCyan, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text(title, color = TextLight, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
                Text(subtitle, color = TextMuted, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
fun NeonStatusChip(text: String, active: Boolean = true) {
    AssistChip(
        onClick = {},
        label = { Text(text) },
        colors = AssistChipDefaults.assistChipColors(
            containerColor = if (active) PrimaryCyan.copy(alpha = .12f) else WarningOrange.copy(alpha = .12f),
            labelColor = if (active) PrimaryCyan else WarningOrange
        )
    )
}

@Composable
fun NeonMetricCard(title: String, value: String, subtitle: String = "", modifier: Modifier = Modifier) {
    NeonSectionCard(modifier) {
        Text(title, color = TextMuted, style = MaterialTheme.typography.labelMedium)
        Text(value, color = PrimaryCyan, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
        if (subtitle.isNotBlank()) Text(subtitle, color = TextMuted, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun NeonActionButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = PrimaryCyan, contentColor = DarkBlue)
    ) { Text(text, fontWeight = FontWeight.ExtraBold) }
}

@Composable
fun NeonOutlinedButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, PrimaryCyan.copy(alpha = .7f))
    ) { Text(text, color = PrimaryCyan, fontWeight = FontWeight.Bold) }
}

@Composable
fun NeonEmptyState(title: String, message: String, action: String? = null, onAction: (() -> Unit)? = null) {
    NeonSectionCard {
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, color = TextLight, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
            Text(message, color = TextMuted, style = MaterialTheme.typography.bodyMedium)
            if (action != null && onAction != null) NeonActionButton(action, onClick = onAction)
        }
    }
}

@Composable
fun NeonErrorState(message: String, action: String = "إعادة المحاولة", onRetry: () -> Unit) {
    NeonSectionCard {
        Text("حدث خطأ", color = ErrorRed, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(message, color = TextMuted)
        NeonOutlinedButton(action, onClick = onRetry)
    }
}

@Composable
fun NeonProcessingState(label: String = "جاري المعالجة…", progress: Float? = null) {
    NeonSectionCard {
        Text(label, color = PrimaryCyan, fontWeight = FontWeight.Bold)
        if (progress == null) CircularProgressIndicator(color = PrimaryCyan)
        else LinearProgressIndicator(
            progress = { progress.coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(),
            color = PrimaryCyan,
            trackColor = DarkBlue
        )
    }
}

@Composable
fun NeonLoading() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = PrimaryCyan)
    }
}
